import json
from pathlib import Path

import pytest

from src.agent.agent import run_agent
from src.common.schemas import (
    Member1Output,
    Member2Output,
    Member3Output,
)
from src.decision.confidence import (
    FEATURE_WEIGHTS,
    get_confidence_label,
)
from src.decision.risk import calculate_refund_risk


PROJECT_ROOT = Path(__file__).resolve().parents[1]

MOCK_CASE_PATH = (
    PROJECT_ROOT
    / "data"
    / "test_cases"
    / "student4_auto_refund.json"
)


def load_case():
    """Load a fresh copy of the valid mock case."""

    with MOCK_CASE_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        raw_data = json.load(file)

    member1 = Member1Output(**raw_data["member1"])
    member2 = Member2Output(**raw_data["member2"])
    member3 = Member3Output(**raw_data["member3"])

    return member1, member2, member3


def test_confidence_weights_sum_to_one():
    assert sum(FEATURE_WEIGHTS.values()) == pytest.approx(1.0)


@pytest.mark.parametrize(
    ("score", "expected_label"),
    [
        (1.00, "HIGH"),
        (0.80, "HIGH"),
        (0.79, "MEDIUM"),
        (0.50, "MEDIUM"),
        (0.49, "LOW"),
        (0.00, "LOW"),
    ],
)
def test_confidence_label_boundaries(
    score,
    expected_label,
):
    assert get_confidence_label(score) == expected_label


@pytest.mark.parametrize(
    ("amount", "expected_risk"),
    [
        (0.00, "LOW"),
        (50.00, "LOW"),
        (50.01, "MEDIUM"),
        (200.00, "MEDIUM"),
        (200.01, "HIGH"),
    ],
)
def test_refund_risk_boundaries(
    amount,
    expected_risk,
):
    assert calculate_refund_risk(amount) == expected_risk


def test_negative_refund_amount_raises_error():
    with pytest.raises(
        ValueError,
        match="refund_amount cannot be negative",
    ):
        calculate_refund_risk(-1.00)


def test_hidden_relevant_region_requests_more_evidence():
    member1, member2, member3 = load_case()

    member1.relevant_region_visible = False

    result = run_agent(
        member1,
        member2,
        member3,
    )

    assert result.decision == "REQUEST_MORE_EVIDENCE"
    assert "not visible" in result.reason.lower()


def test_invalid_order_requires_human_review():
    member1, member2, member3 = load_case()

    member3.order_valid = False

    result = run_agent(
        member1,
        member2,
        member3,
    )

    assert result.decision == "HUMAN_REVIEW"
    assert "order" in result.reason.lower()


def test_ineligible_policy_requires_human_review():
    member1, member2, member3 = load_case()

    member3.policy_eligible = False

    result = run_agent(
        member1,
        member2,
        member3,
    )

    assert result.decision == "HUMAN_REVIEW"
    assert "policy" in result.reason.lower()


def test_no_detected_damage_requests_more_evidence():
    member1, member2, member3 = load_case()

    member2.damage_detected = False

    result = run_agent(
        member1,
        member2,
        member3,
    )

    assert result.decision == "REQUEST_MORE_EVIDENCE"
    assert "damage" in result.reason.lower()


def test_low_claim_image_consistency_requests_more_evidence():
    member1, member2, member3 = load_case()

    member2.claim_image_consistency = 0.40

    result = run_agent(
        member1,
        member2,
        member3,
    )

    assert result.decision == "REQUEST_MORE_EVIDENCE"
    assert "claim" in result.reason.lower()


def test_mismatched_case_ids_raise_error():
    member1, member2, member3 = load_case()

    member3.case_id = "DIFFERENT_CASE"

    with pytest.raises(
        ValueError,
        match="different case_id",
    ):
        run_agent(
            member1,
            member2,
            member3,
        )


def test_invalid_evidence_score_raises_error():
    member1, member2, member3 = load_case()

    member1.image_quality = 1.20

    with pytest.raises(
        ValueError,
        match="image_quality",
    ):
        run_agent(
            member1,
            member2,
            member3,
        )