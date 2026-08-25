import json

from src.agent.agent import run_agent
from src.common.schemas import (
    Member1Output,
    Member2Output,
    Member3Output,
)


def load_mock_case(filename):
    with open(filename, "r", encoding="utf-8") as file:
        raw_data = json.load(file)

    member1 = Member1Output(**raw_data["member1"])
    member2 = Member2Output(**raw_data["member2"])
    member3 = Member3Output(**raw_data["member3"])

    return member1, member2, member3


def test_auto_refund_case():
    member1, member2, member3 = load_mock_case(
        "data/test_cases/student4_auto_refund.json"
    )

    result = run_agent(member1, member2, member3)

    assert result.case_id == "REFUND_001"
    assert result.evidence_confidence >= 0.80
    assert result.refund_risk == "LOW"
    assert result.decision == "AUTO_REFUND"


def test_unusable_image_requests_more_evidence():
    member1, member2, member3 = load_mock_case(
        "data/test_cases/student4_auto_refund.json"
    )

    member1.image_usable = False

    result = run_agent(member1, member2, member3)

    assert result.decision == "REQUEST_MORE_EVIDENCE"


def test_high_value_refund_requires_review():
    member1, member2, member3 = load_mock_case(
        "data/test_cases/student4_auto_refund.json"
    )

    member3.refund_amount = 700.0

    result = run_agent(member1, member2, member3)

    assert result.refund_risk == "HIGH"
    assert result.decision == "HUMAN_REVIEW"