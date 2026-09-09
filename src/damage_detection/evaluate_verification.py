"""Evaluate Week3 claim-verification decisions from explicit input/output cases."""
from __future__ import annotations
import argparse
import json
from collections import Counter
from pathlib import Path
from src.common.schemas import CaseInput, Member1Output, Member2Output
from src.damage_detection.verification import verify_claim

LABELS = ("positive", "negative", "ambiguous")


def metrics(expected: list[str], predicted: list[str]) -> dict:
    if not expected or len(expected) != len(predicted):
        raise ValueError("expected and predicted must be non-empty and equal length")
    if any(label not in LABELS for label in expected + predicted):
        raise ValueError("unknown verdict label")
    per_class = {}
    for label in LABELS:
        tp = sum(a == label and b == label for a, b in zip(expected, predicted))
        fp = sum(a != label and b == label for a, b in zip(expected, predicted))
        fn = sum(a == label and b != label for a, b in zip(expected, predicted))
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[label] = {"precision": precision, "recall": recall, "f1": f1,
                            "support": expected.count(label)}
    return {"cases": len(expected),
            "accuracy": sum(a == b for a, b in zip(expected, predicted)) / len(expected),
            "macro_precision": sum(v["precision"] for v in per_class.values()) / len(LABELS),
            "macro_recall": sum(v["recall"] for v in per_class.values()) / len(LABELS),
            "macro_f1": sum(v["f1"] for v in per_class.values()) / len(LABELS),
            "per_class": per_class,
            "expected_counts": dict(Counter(expected)), "predicted_counts": dict(Counter(predicted))}


def evaluate(payload: dict) -> dict:
    expected, predicted, results = [], [], []
    for item in payload["cases"]:
        parts = {name: dict(payload["base"][name]) | item.get(name, {})
                 for name in ("case", "member1", "member2")}
        case_id = item["case_id"]
        for part in parts.values():
            part["case_id"] = case_id
        result = verify_claim(CaseInput.model_validate(parts["case"]),
                              Member1Output.model_validate(parts["member1"]),
                              Member2Output.model_validate(parts["member2"]))
        expected.append(item["expected_verdict"])
        predicted.append(result.verdict)
        results.append({"case_id": result.member2.case_id, "expected": item["expected_verdict"],
                        "predicted": result.verdict, "reason_code": result.reason_code})
    report = metrics(expected, predicted)
    report.update(evaluation_name="Week3 claim-verification contract regression",
                  scope="rule_and_interface_behaviour_only",
                  includes_visual_model_inference=False,
                  includes_location_cases=True,
                  limitation=("Metrics validate specified verification behaviour on synthetic contract "
                              "cases. They are not visual-model or real-world accuracy estimates."),
                  case_results=results)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cases", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = evaluate(json.loads(args.cases.read_text(encoding="utf-8")))
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in
                      ("cases", "accuracy", "macro_precision", "macro_recall", "macro_f1")}, indent=2))
