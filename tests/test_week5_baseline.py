import json

import pytest

from src.agent.evidence_agent import evidence_features_from_case, run_evidence_case
from src.decision.baseline import calculate_feature_confidence


def load_refund_case():
    with open("data/test_cases/refund_001.json", encoding="utf-8") as case_file:
        return json.load(case_file)


def test_refund_001_runs_through_week5_baseline():
    case = load_refund_case()

    result = run_evidence_case(case)

    assert result.evidence_confidence == 0.92
    assert result.confidence_label == "HIGH"
    assert result.refund_risk == "MEDIUM"
    assert result.decision == case["expected_decision"]


def test_policy_ineligible_case_requires_human_review():
    case = load_refund_case()
    case["evidence_features"]["policy_eligible"] = False

    result = run_evidence_case(case)

    assert result.decision == "HUMAN_REVIEW"


@pytest.mark.parametrize("invalid_score", [-0.01, 1.01])
def test_confidence_rejects_out_of_range_features(invalid_score):
    case = load_refund_case()
    features = evidence_features_from_case(case)
    features.image_quality = invalid_score

    with pytest.raises(ValueError):
        calculate_feature_confidence(features)
