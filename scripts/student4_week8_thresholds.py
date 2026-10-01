"""Validation-only confidence-threshold sensitivity experiment."""

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


HIGH_THRESHOLDS = (0.70, 0.80, 0.90, 0.95)
MEDIUM_THRESHOLD = 0.50

DECISIONS = {
    "AUTO_REFUND",
    "REQUEST_MORE_EVIDENCE",
    "HUMAN_REVIEW",
}


def confidence_label(score, high_threshold):
    if score >= high_threshold:
        return "HIGH"
    if score >= MEDIUM_THRESHOLD:
        return "MEDIUM"
    return "LOW"


def main():
    input_path = DATA_DIR / "validation_inputs.json"
    label_path = DATA_DIR / "validation_labels.json"

    inputs = read_json(input_path)
    label_rows = read_json(label_path)

    input_ids = [case["case_id"] for case in inputs]
    label_ids = [row["case_id"] for row in label_rows]

    if not inputs:
        raise ValueError("Validation inputs are empty.")

    if len(input_ids) != len(set(input_ids)):
        raise ValueError("Duplicate input case IDs.")

    if len(label_ids) != len(set(label_ids)):
        raise ValueError("Duplicate label case IDs.")

    if set(input_ids) != set(label_ids):
        raise ValueError("Input and label case IDs differ.")

    labels = {
        row["case_id"]: row["expected_decision"]
        for row in label_rows
    }

    if not set(labels.values()).issubset(DECISIONS):
        raise ValueError("Unsupported expected decision.")

    model = joblib.load(MODEL_PATH)
    experiments = []

    print(
        "method threshold matched auto wrong_auto review evidence"
    )

    for method in ("rule", "ml"):
        scored_cases = []

        # Calculate each method's score once per case.
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

            scored_cases.append(
                (case["case_id"], members, baseline)
            )

        for threshold in HIGH_THRESHOLDS:
            rows = []

            for case_id, members, baseline in scored_cases:
                label = confidence_label(
                    baseline.evidence_confidence,
                    threshold,
                )

                # Reuse all existing overrides and the decision matrix.
                predicted, reason = make_decision(
                    label,
                    baseline.refund_risk,
                    *members,
                )

                expected = labels[case_id]

                rows.append(
                    {
                        "case_id": case_id,
                        "evidence_confidence": (
                            baseline.evidence_confidence
                        ),
                        "confidence_label": label,
                        "refund_risk": baseline.refund_risk,
                        "expected_decision": expected,
                        "predicted_decision": predicted,
                        "correct": predicted == expected,
                        "reason": reason,
                    }
                )

            correct = sum(row["correct"] for row in rows)
            auto = sum(
                row["predicted_decision"] == "AUTO_REFUND"
                for row in rows
            )
            wrong_auto = sum(
                row["predicted_decision"] == "AUTO_REFUND"
                and row["expected_decision"] != "AUTO_REFUND"
                for row in rows
            )
            review = sum(
                row["predicted_decision"] == "HUMAN_REVIEW"
                for row in rows
            )
            evidence = sum(
                row["predicted_decision"] == "REQUEST_MORE_EVIDENCE"
                for row in rows
            )

            experiments.append(
                {
                    "method": method,
                    "high_threshold": threshold,
                    "medium_threshold": MEDIUM_THRESHOLD,
                    "total_cases": len(rows),
                    "correct_cases": correct,
                    "agreement_with_synthetic_labels": (
                        correct / len(rows)
                    ),
                    "auto_refund_count": auto,
                    "incorrect_auto_refund_count": wrong_auto,
                    "human_review_count": review,
                    "request_more_evidence_count": evidence,
                    "cases": rows,
                }
            )

            print(
                f"{method:6} {threshold:.2f}      "
                f"{correct:2}/{len(rows)}   "
                f"{auto:4} {wrong_auto:10} "
                f"{review:6} {evidence:8}"
            )

    report = {
        "dataset_type": "synthetic_pilot",
        "split": "validation",
        "input_sha256": file_hash(input_path),
        "label_sha256": file_hash(label_path),
        "model_sha256": file_hash(MODEL_PATH),
        "score_precision": (
            "Existing Agent scores rounded to two decimal places."
        ),
        "limitations": (
            "Sensitivity analysis against a rule-derived rubric. "
            "Does not identify a real-world optimal threshold."
        ),
        "experiments": experiments,
    }

    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = RESULT_DIR / "validation_thresholds.json"
    output_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"\nSaved: {output_path}")
    print("The test split was not evaluated.")
    print("The application defaults were not changed.")


if __name__ == "__main__":
    main()