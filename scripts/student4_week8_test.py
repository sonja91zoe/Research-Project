"""Evaluate frozen pilot settings on the held-out test cases."""

import json

import joblib

from scripts.student4_week8_evaluate import (
    DATA_DIR,
    MODEL_PATH,
    RESULT_DIR,
    file_hash,
    read_json,
)
from src.agent.agent import run_agent
from src.common.schemas import (
    Member1Output,
    Member2Output,
    Member3Output,
)
from src.decision.decision import make_decision


DECISIONS = {
    "AUTO_REFUND",
    "REQUEST_MORE_EVIDENCE",
    "HUMAN_REVIEW",
}


def main():
    config_path = DATA_DIR / "experiment_config.json"
    input_path = DATA_DIR / "test_inputs.json"
    label_path = DATA_DIR / "test_labels.json"
    output_path = RESULT_DIR / "test_comparison.json"

    # Protect an existing evaluation record from accidental overwrite.
    if output_path.exists():
        raise FileExistsError(
            "test_comparison.json already exists. "
            "Inspect the saved result before rerunning."
        )

    config = read_json(config_path)
    inputs = read_json(input_path)
    label_rows = read_json(label_path)

    input_ids = [case["case_id"] for case in inputs]
    label_ids = [row["case_id"] for row in label_rows]

    if not inputs:
        raise ValueError("Test inputs are empty.")

    if (
        len(input_ids) != len(set(input_ids))
        or len(label_ids) != len(set(label_ids))
        or set(input_ids) != set(label_ids)
    ):
        raise ValueError("Invalid or mismatched case IDs.")

    labels = {
        row["case_id"]: row["expected_decision"]
        for row in label_rows
    }

    if not set(labels.values()).issubset(DECISIONS):
        raise ValueError("Unsupported expected decision.")

    model = joblib.load(MODEL_PATH)
    report = {
        "dataset_type": "synthetic_pilot",
        "split": "test",
        "config": config,
        "config_sha256": file_hash(config_path),
        "input_sha256": file_hash(input_path),
        "label_sha256": file_hash(label_path),
        "model_sha256": file_hash(MODEL_PATH),
        "methods": {},
    }

    for method in ("rule", "ml"):
        high = config["high_thresholds"][method]
        medium = config["medium_threshold"]

        if not 0 <= medium < high <= 1:
            raise ValueError("Invalid confidence thresholds.")

        rows = []

        for case in inputs:
            members = (
                Member1Output(**case["member1"]),
                Member2Output(**case["member2"]),
                Member3Output(**case["member3"]),
            )

            if any(
                member.case_id != case["case_id"]
                for member in members
            ):
                raise ValueError("Case IDs do not match.")

            baseline = run_agent(
                *members,
                confidence_method=method,
                model=model if method == "ml" else None,
            )

            score = baseline.evidence_confidence
            confidence = (
                "HIGH" if score >= high
                else "MEDIUM" if score >= medium
                else "LOW"
            )

            predicted, reason = make_decision(
                confidence,
                baseline.refund_risk,
                *members,
            )

            expected = labels[case["case_id"]]
            rows.append(
                {
                    "case_id": case["case_id"],
                    "expected_decision": expected,
                    "predicted_decision": predicted,
                    "correct": predicted == expected,
                    "evidence_confidence": score,
                    "refund_risk": baseline.refund_risk,
                    "reason": reason,
                }
            )

        correct = sum(row["correct"] for row in rows)
        wrong_auto = sum(
            row["predicted_decision"] == "AUTO_REFUND"
            and row["expected_decision"] != "AUTO_REFUND"
            for row in rows
        )

        report["methods"][method] = {
            "high_threshold": high,
            "total_cases": len(rows),
            "correct_cases": correct,
            "agreement_with_synthetic_labels": correct / len(rows),
            "incorrect_auto_refund_count": wrong_auto,
            "predicted_counts": {
                decision: sum(
                    row["predicted_decision"] == decision
                    for row in rows
                )
                for decision in sorted(DECISIONS)
            },
            "cases": rows,
        }

        print(f"\nMethod: {method}; threshold: {high:.2f}")
        print(f"Label agreement: {correct}/{len(rows)}")
        print(f"Incorrect auto-refunds: {wrong_auto}")

        for row in rows:
            status = "MATCH" if row["correct"] else "MISMATCH"
            print(
                f"{row['case_id']} | "
                f"{row['predicted_decision']} | "
                f"confidence={row['evidence_confidence']:.2f} | "
                f"{status}"
            )

    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"\nSaved: {output_path}")
    print("Application defaults were not changed.")


if __name__ == "__main__":
    main()