"""Compare rule and ML decisions on the Week 8 validation pilot.

This measures agreement with synthetic scenario labels.
It does not measure real-world refund accuracy.
"""

import hashlib
import json
from collections import Counter
from pathlib import Path

import joblib

from src.agent.agent import run_agent
from src.common.schemas import (
    Member1Output,
    Member2Output,
    Member3Output,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data" / "member4" / "week8"
RESULT_DIR = PROJECT_ROOT / "data" / "results" / "student4_week8"
MODEL_PATH = (
    PROJECT_ROOT
    / "models"
    / "student4_evidence_confidence_v1.joblib"
)

DECISIONS = [
    "AUTO_REFUND",
    "REQUEST_MORE_EVIDENCE",
    "HUMAN_REVIEW",
]


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evaluate_method(inputs, labels, method, model=None):
    rows = []

    for case in inputs:
        member1 = Member1Output(**case["member1"])
        member2 = Member2Output(**case["member2"])
        member3 = Member3Output(**case["member3"])

        if {
            case["case_id"],
            member1.case_id,
            member2.case_id,
            member3.case_id,
        } != {case["case_id"]}:
            raise ValueError("Case IDs do not match.")

        # Only evidence inputs are sent to the Agent.
        result = run_agent(
            member1,
            member2,
            member3,
            confidence_method=method,
            model=model,
        )

        expected = labels[case["case_id"]]["expected_decision"]
        predicted = result.decision

        if expected not in DECISIONS or predicted not in DECISIONS:
            raise ValueError("Unsupported decision label.")

        rows.append(
            {
                "case_id": case["case_id"],
                "expected_decision": expected,
                "predicted_decision": predicted,
                "correct": predicted == expected,
                "evidence_confidence": result.evidence_confidence,
                "refund_risk": result.refund_risk,
                "reason": result.reason,
            }
        )

    correct = sum(row["correct"] for row in rows)

    # Rows represent expected labels; columns represent predictions.
    matrix = [[0 for _ in DECISIONS] for _ in DECISIONS]

    for row in rows:
        expected_index = DECISIONS.index(row["expected_decision"])
        predicted_index = DECISIONS.index(row["predicted_decision"])
        matrix[expected_index][predicted_index] += 1

    predicted_counts = Counter(
        row["predicted_decision"] for row in rows
    )

    summary = {
        "total_cases": len(rows),
        "correct_cases": correct,
        "agreement_with_synthetic_labels": correct / len(rows),
        "predicted_counts": {
            decision: predicted_counts[decision]
            for decision in DECISIONS
        },
        "incorrect_auto_refund_count": sum(
            row["predicted_decision"] == "AUTO_REFUND"
            and row["expected_decision"] != "AUTO_REFUND"
            for row in rows
        ),
        "unnecessary_review_count": sum(
            row["predicted_decision"] == "HUMAN_REVIEW"
            and row["expected_decision"] != "HUMAN_REVIEW"
            for row in rows
        ),
        "unnecessary_evidence_request_count": sum(
            row["predicted_decision"] == "REQUEST_MORE_EVIDENCE"
            and row["expected_decision"] != "REQUEST_MORE_EVIDENCE"
            for row in rows
        ),
        "confusion_matrix_label_order": DECISIONS,
        "confusion_matrix": matrix,
    }

    return {"summary": summary, "cases": rows}


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

    labels = {row["case_id"]: row for row in label_rows}
    model = joblib.load(MODEL_PATH)

    report = {
        "dataset_type": "synthetic_pilot",
        "split": "validation",
        "limitations": (
            "Small controlled scenario set; label agreement does not "
            "establish real-world accuracy or model superiority."
        ),
        "input_sha256": file_hash(input_path),
        "label_sha256": file_hash(label_path),
        "model_sha256": file_hash(MODEL_PATH),
        "methods": {},
    }

    for method in ("rule", "ml"):
        result = evaluate_method(
            inputs,
            labels,
            method,
            model=model if method == "ml" else None,
        )
        report["methods"][method] = result

        summary = result["summary"]

        print(f"\nMethod: {method}")
        print(
            f"Label agreement: "
            f"{summary['correct_cases']}/{summary['total_cases']}"
        )

        for row in result["cases"]:
            status = "MATCH" if row["correct"] else "MISMATCH"
            print(
                f"{row['case_id']} | "
                f"{row['predicted_decision']} | "
                f"confidence={row['evidence_confidence']:.2f} | "
                f"{status}"
            )

    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = RESULT_DIR / "validation_comparison.json"
    output_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"\nSaved: {output_path}")
    print("The test split was not evaluated.")


if __name__ == "__main__":
    main()