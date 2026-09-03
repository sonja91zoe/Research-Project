import json

import pytest

from src.common.schemas import CaseInput, Member1Output, Member2Output
from src.evidence.pipeline import build_evidence_chain, evidence_chain_to_dict


def load_single_case():
    with open(
        "data/test_cases/member3_week6_single_case.json", encoding="utf-8"
    ) as case_file:
        raw = json.load(case_file)
    return (
        raw,
        CaseInput(**raw["case_input"]),
        Member1Output(**raw["member1"]),
        Member2Output(**raw["member2"]),
    )


def test_single_case_builds_complete_traceable_evidence_chain():
    raw, case_input, member1, member2 = load_single_case()

    chain = build_evidence_chain(case_input, member1, member2, raw["request_date"])
    output = chain.member3_output

    assert output["order_valid"] is raw["expected"]["order_valid"]
    assert output["image_order_consistency"] == raw["expected"]["image_order_consistency"]
    assert output["policy_eligible"] is raw["expected"]["policy_eligible"]
    assert output["refund_amount"] == raw["expected"]["refund_amount"]
    assert chain.order_evidence.order_id == "ORD001"
    assert chain.policy_evidence.policy_id == "POL-DAMAGE-30"
    assert chain.verified_evidence.policy_source
    assert evidence_chain_to_dict(chain)["case_id"] == "M3_W6_001"


def test_unusable_image_is_not_policy_eligible():
    raw, case_input, member1, member2 = load_single_case()
    member1.image_usable = False

    chain = build_evidence_chain(case_input, member1, member2, raw["request_date"])

    assert chain.member3_output["policy_eligible"] is False
    assert chain.verified_evidence.reason == "Submitted image evidence is not usable."


def test_low_claim_image_consistency_is_not_policy_eligible():
    raw, case_input, member1, member2 = load_single_case()
    member2.claim_image_consistency = 0.30

    chain = build_evidence_chain(case_input, member1, member2, raw["request_date"])

    assert chain.member3_output["policy_eligible"] is False
    assert "does not sufficiently support" in chain.verified_evidence.reason


def test_mismatched_case_ids_are_rejected():
    raw, case_input, member1, member2 = load_single_case()
    member2.case_id = "DIFFERENT_CASE"

    with pytest.raises(ValueError, match="different case_id"):
        build_evidence_chain(case_input, member1, member2, raw["request_date"])
