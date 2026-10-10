import json

from scripts.member3_week8_generate_dataset import build_cases
from scripts.member3_week8_evaluate_rag import evaluate
from scripts.member3_week9_final_evaluation import (
    _adapt_legacy_visual_product,
    build_final_results,
)
from scripts.member3_week9_generate_evidence_dataset import (
    build_cases as build_evidence_cases,
)
from scripts.member3_generate_mock_orders import build_orders
from src.evidence.rag import classify_policy_intent, retrieve_best_policy
from src.evidence.verification import verify_case


def test_intent_router_handles_the_four_policy_families():
    examples = {
        "The jacket arrived with a tear.": "POL-DAMAGE-30",
        "I received the wrong item.": "POL-WRONG-ITEM-14",
        "The photo shows no visible damage.": "POL-NO-DAMAGE",
        "This clearance item was final sale.": "POL-FINAL-SALE",
    }

    for query, expected in examples.items():
        assert classify_policy_intent(query) == expected
        assert retrieve_best_policy(query).policy_id == expected


def test_refined_retrieval_improves_the_frozen_week8_baseline():
    cases = build_cases()
    baseline = evaluate(cases, strategy="lexical")
    refined = evaluate(cases, strategy="intent_aware")

    assert 0.0 <= baseline["top_1_accuracy"] <= 1.0
    assert refined["top_1_accuracy"] >= 0.95
    assert refined["top_1_accuracy"] > baseline["top_1_accuracy"]
    assert len(refined["top_1_failures"]) < len(baseline["top_1_failures"])


def test_final_evidence_regression_matches_all_expected_labels():
    results = build_final_results()
    regression = results["evidence_regression"]

    assert regression["total_cases"] == 12
    assert regression["passed_cases"] == 12
    assert regression["pass_rate"] == 1.0
    assert regression["failures"] == []


def test_legacy_name_adapter_requires_usable_independent_product_evidence():
    case = next(
        case for case in build_evidence_cases()
        if case["scenario"] == "product_mismatch"
    )
    assert case["detected_product"] == "Grey Hoodie"
    assert verify_case(case).image_order_match_status == "NOT_AVAILABLE"

    adapted = _adapt_legacy_visual_product(case)
    assert adapted["detected_product"] == "hoodie"
    assert case["detected_product"] == "Grey Hoodie"
    result = verify_case(adapted)
    assert result.image_order_match_status == "MISMATCH"
    assert result.policy_eligible is False

    for missing_evidence in (
        {"image_present": False},
        {"image_usable": False},
        {"detected_product": None},
        {"detected_product": "Unknown Jacket"},
        {"product_confidence": 0.1},
    ):
        untrusted = _adapt_legacy_visual_product({**case, **missing_evidence})
        assert verify_case(untrusted).image_order_match_status == "NOT_AVAILABLE"


def test_week9_evidence_dataset_is_balanced_across_ten_scenarios():
    cases = build_evidence_cases()
    counts = {}
    for case in cases:
        counts[case["scenario"]] = counts.get(case["scenario"], 0) + 1

    assert len(cases) == 120
    assert len(counts) == 10
    assert set(counts.values()) == {12}
    assert all(
        case["dataset_type"] == "synthetic_balanced_evidence_evaluation"
        for case in cases
    )


def test_week9_evidence_validation_has_no_label_or_reason_failures():
    validation = build_final_results()["evidence_validation"]

    assert validation["total_cases"] == 120
    assert validation["passed_cases"] == 120
    assert validation["failures"] == []
    assert set(validation["scenario_pass_rates"].values()) == {1.0}
    assert validation["eligibility_confusion_matrix"] == {
        "true_positive": 24,
        "true_negative": 96,
        "false_positive": 0,
        "false_negative": 0,
    }


def test_saved_week9_results_match_reproducible_evaluation():
    with open("data/results/member3_week9_final_results.json", encoding="utf-8") as file:
        saved = json.load(file)

    assert saved == build_final_results()


def test_mock_order_expansion_preserves_original_records():
    with open("data/orders/orders.json", encoding="utf-8") as file:
        saved = json.load(file)

    from scripts.member3_generate_mock_orders import add_provenance

    regenerated = add_provenance(build_orders(saved[:12]))
    assert len(saved) == 70
    assert saved == regenerated
    assert saved[0]["order_id"] == "ORD001"
    assert saved[11]["order_id"] == "ORD012"
    assert saved[12]["order_id"] == "ORD013"
    assert saved[-1]["order_id"] == "ORD070"
    assert all(order["data_type"] == "synthetic_order" for order in saved)
    assert all(order["image_evidence"] is not None for order in saved)
    assert len({
        order["image_evidence"]["source_image_id"]
        for order in saved if order["image_evidence"] is not None
    }) == 70
