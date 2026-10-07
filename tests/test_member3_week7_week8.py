import json

from app.server import run_evidence_case
from scripts.member3_week8_evaluate_rag import evaluate
from scripts.member3_week8_generate_dataset import build_cases


def test_week7_app_runs_complete_backend_chain():
    result = run_evidence_case(
        {
            "order_id": "ORD001",
            "claim_text": "The black jacket arrived with a tear on the left sleeve.",
            "detected_product": "Black Jacket",
            "damage_type": "hole_or_tear",
            "image_present": True,
        }
    )

    assert result["order"]["order_id"] == "ORD001"
    assert result["policy"]["policy_id"] == "POL-DAMAGE-30"
    assert result["evidence"]["policy_eligible"] is True
    assert result["decision"]["decision"] in {
        "AUTO_REFUND",
        "REQUEST_MORE_EVIDENCE",
        "HUMAN_REVIEW",
    }
    assert len(result["adopted_rules"]) == 3


def test_week7_missing_image_returns_explainable_feedback():
    result = run_evidence_case(
        {
            "order_id": "ORD001",
            "claim_text": "The black jacket arrived damaged.",
            "detected_product": "Black Jacket",
            "damage_type": "hole_or_tear",
            "image_present": False,
        }
    )

    assert result["evidence"]["policy_eligible"] is False
    assert result["reason"] == "Required image evidence is missing."


def test_week7_missing_product_prediction_is_not_self_filled_from_order():
    result = run_evidence_case(
        {
            "order_id": "ORD001",
            "claim_text": "The black jacket arrived with a tear.",
            "damage_type": "hole_or_tear",
            "image_present": True,
        }
    )

    assert result["evidence"]["image_order_match_status"] == "NOT_AVAILABLE"
    assert result["evidence"]["image_order_consistency"] == 0.5
    assert result["evidence"]["policy_eligible"] is True


def test_week8_dataset_has_sixty_balanced_labelled_cases():
    cases = build_cases()
    counts = {}
    for case in cases:
        counts[case["expected_policy_id"]] = counts.get(case["expected_policy_id"], 0) + 1

    assert len(cases) == 60
    assert set(counts.values()) == {15}
    assert all(case["dataset_type"] == "synthetic_labelled_evaluation" for case in cases)


def test_week8_metrics_are_valid_and_reproducible():
    metrics = evaluate(build_cases())

    assert metrics["total_cases"] == 60
    assert 0.0 <= metrics["top_1_accuracy"] <= 1.0
    assert 0.0 <= metrics["hit_rate_at_3"] <= 1.0
    assert 0.0 <= metrics["mean_reciprocal_rank"] <= 1.0


def test_saved_week8_dataset_matches_generator():
    with open(
        "data/test_cases/member3_week8_rag_evaluation.json", encoding="utf-8"
    ) as dataset_file:
        saved = json.load(dataset_file)

    assert saved == build_cases()
