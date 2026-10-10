"""Run the final Member 3 retrieval and evidence regression evaluation."""

import json
from collections import Counter
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.member3_week8_evaluate_rag import evaluate
from src.evidence.verification import verify_case


RETRIEVAL_DATASET = PROJECT_ROOT / "data/test_cases/member3_week8_rag_evaluation.json"
EVIDENCE_DATASET = PROJECT_ROOT / "data/test_cases/member3_cases.json"
EVIDENCE_VALIDATION_DATASET = (
    PROJECT_ROOT / "data/test_cases/member3_week9_evidence_evaluation.json"
)
OUTPUT = PROJECT_ROOT / "data/results/member3_week9_final_results.json"

# The frozen synthetic cases predate category-only Member 2 predictions. Their
# detected_product field is a simulated image observation, not an order name.
# Translate only the exact labels present in that legacy evaluation. Runtime
# product matching remains strict and never parses free-form product names.
LEGACY_DETECTED_PRODUCT_CATEGORIES = {
    "black jacket": "jacket",
    "blue jacket": "jacket",
    "leather jacket": "jacket",
    "red jacket": "jacket",
    "black hoodie": "hoodie",
    "cream hoodie": "hoodie",
    "green hoodie": "hoodie",
    "grey hoodie": "hoodie",
    "navy t-shirt": "t-shirt",
    "white t-shirt": "t-shirt",
    "yellow t-shirt": "t-shirt",
}


def _load(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def _adapt_legacy_visual_product(case: dict) -> dict:
    """Adapt known synthetic visual labels without inferring from the order."""

    if (
        not case.get("image_present", False)
        or not case.get("image_usable", True)
        or case.get("product_confidence") is not None
    ):
        return case
    detected = case.get("detected_product")
    if not isinstance(detected, str):
        return case
    category = LEGACY_DETECTED_PRODUCT_CATEGORIES.get(
        " ".join(detected.strip().casefold().split())
    )
    return {**case, "detected_product": category} if category else case


def evaluate_evidence_regression(cases: list[dict]) -> dict[str, object]:
    failures = []
    reason_counts: Counter[str] = Counter()
    scenario_totals: Counter[str] = Counter()
    scenario_passed: Counter[str] = Counter()
    confusion = {"true_positive": 0, "true_negative": 0, "false_positive": 0, "false_negative": 0}

    for case in cases:
        result = verify_case(_adapt_legacy_visual_product(case))
        reason_counts[result.reason] += 1
        scenario = case.get("scenario", "legacy_regression")
        scenario_totals[scenario] += 1
        eligibility_matches = result.policy_eligible == case["expected_eligible"]
        reason_matches = (
            "expected_reason" not in case or result.reason == case["expected_reason"]
        )
        if eligibility_matches and reason_matches:
            scenario_passed[scenario] += 1
        else:
            failures.append(
                {
                    "case_id": case["case_id"],
                    "expected_eligible": case["expected_eligible"],
                    "actual_eligible": result.policy_eligible,
                    "expected_reason": case.get("expected_reason"),
                    "reason": result.reason,
                }
            )

        if case["expected_eligible"] and result.policy_eligible:
            confusion["true_positive"] += 1
        elif not case["expected_eligible"] and not result.policy_eligible:
            confusion["true_negative"] += 1
        elif result.policy_eligible:
            confusion["false_positive"] += 1
        else:
            confusion["false_negative"] += 1

    passed = len(cases) - len(failures)
    return {
        "total_cases": len(cases),
        "passed_cases": passed,
        "pass_rate": passed / len(cases) if cases else 0.0,
        "failures": failures,
        "outcome_reason_counts": dict(sorted(reason_counts.items())),
        "eligibility_confusion_matrix": confusion,
        "scenario_pass_rates": {
            scenario: scenario_passed[scenario] / total
            for scenario, total in sorted(scenario_totals.items())
        },
    }


def build_final_results() -> dict[str, object]:
    retrieval_cases = _load(RETRIEVAL_DATASET)
    evidence_cases = _load(EVIDENCE_DATASET)
    evidence_validation_cases = _load(EVIDENCE_VALIDATION_DATASET)
    baseline = evaluate(retrieval_cases, strategy="lexical")
    refined = evaluate(retrieval_cases, strategy="intent_aware")

    baseline_failure_ids = {
        failure["case_id"] for failure in baseline["top_1_failures"]
    }
    refined_failure_ids = {
        failure["case_id"] for failure in refined["top_1_failures"]
    }

    return {
        "evaluation_name": "Member 3 Week 9 final retrieval and evidence evaluation",
        "dataset_type": "synthetic_labelled_evaluation",
        "retrieval_comparison": {
            "baseline": baseline,
            "refined": refined,
            "top_1_absolute_improvement": (
                refined["top_1_accuracy"] - baseline["top_1_accuracy"]
            ),
            "resolved_baseline_failure_case_ids": sorted(
                baseline_failure_ids - refined_failure_ids
            ),
            "new_regression_case_ids": sorted(
                refined_failure_ids - baseline_failure_ids
            ),
        },
        "evidence_regression": evaluate_evidence_regression(evidence_cases),
        "evidence_validation": evaluate_evidence_regression(evidence_validation_cases),
        "limitations": [
            "All evaluation records are synthetic or controlled project data.",
            "The policy corpus contains selected official H&M, Zara and UNIQLO Australia clauses plus clearly labelled internal safety rules.",
            "Intent routing is deterministic and has not been validated on real claims.",
            "Image-model accuracy is outside the Member 3 retrieval evaluation.",
        ],
    }


def main() -> None:
    results = build_final_results()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    comparison = results["retrieval_comparison"]
    evidence = results["evidence_regression"]
    validation = results["evidence_validation"]
    print(f"Baseline Top-1: {comparison['baseline']['top_1_accuracy']:.3f}")
    print(f"Refined Top-1:  {comparison['refined']['top_1_accuracy']:.3f}")
    print(f"Evidence cases: {evidence['passed_cases']}/{evidence['total_cases']} passed")
    print(
        "Evidence validation: "
        f"{validation['passed_cases']}/{validation['total_cases']} passed"
    )
    print(f"Wrote {OUTPUT.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
