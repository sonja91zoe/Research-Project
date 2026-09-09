import csv
import json
from pathlib import Path

import pytest
from pydantic import ValidationError
from src.common.schemas import CaseInput, Member1Output, Member2Output
from src.damage_detection.verification import HandoffContext, verify_claim, recommend_handoff
from src.damage_detection.prepare_week3 import prepare
from src.damage_detection.week3_demo import run


def inputs():
    case = CaseInput(case_id="refund_001", order_id="order_001",
                     claim_text="The garment has a hole.", image_paths=["fixture.jpg"])
    quality = Member1Output(case_id=case.case_id, claimed_defect="hole", image_quality=0.9,
                            blur_score=0.9, lighting_score=0.9,
                            relevant_region_visible=True, image_usable=True)
    visual = Member2Output(case_id=case.case_id, damage_detected=True,
                           damage_type="hole_or_tear", damage_confidence=0.9)
    context = HandoffContext(case_id=case.case_id, risk_score=0.1, order_valid=True,
                              policy_eligible=True, evidence_complete=True,
                              image_order_verified=True)
    return case, quality, visual, context


def test_matching_claim_integrates_without_mutation():
    c, q, v, h = inputs()
    result = verify_claim(c, q, v)
    assert result.verdict == "positive"
    assert result.member2.claim_image_consistency == 1.0
    assert v.claim_image_consistency is None
    assert recommend_handoff(result, h).decision == "Auto Refund"


def test_mismatch_is_manual_not_refund_or_automatic_rejection():
    c, q, v, h = inputs()
    q.claimed_defect = "stain"
    result = verify_claim(c, q, v)
    assert result.verdict == "negative"
    assert result.consistency_score == 0
    assert recommend_handoff(result, h).decision == "Manual Review"


@pytest.mark.parametrize("field,value", [("claimed_defect", None), ("claimed_defect", "no hole"),
    ("claimed_defect", "hole and stain"), ("claimed_defect", "wrong size"),
    ("image_usable", False), ("relevant_region_visible", False),
    ("claimed_location", "sleeve"), ("product", "shirt")])
def test_unsupported_or_insufficient_claim_abstains(field, value):
    c, q, v, h = inputs()
    setattr(q, field, value)
    result = verify_claim(c, q, v)
    assert result.verdict == "ambiguous"
    assert result.consistency_score is None
    assert recommend_handoff(result, h).decision == "Request Evidence"


@pytest.mark.parametrize("confidence,positive", [(0.6999, False), (0.70, True), (1.0, True)])
def test_review_boundary(confidence, positive):
    c, q, v, _ = inputs()
    v.damage_confidence = confidence
    assert (verify_claim(c, q, v).verdict == "positive") is positive


@pytest.mark.parametrize("change", [{"evidence_quality": "poor"}, {"evidence_quality": "unusable"},
    {"needs_human_review": True}, {"damage_type": "no_damage", "damage_detected": False},
    {"damage_type": "uncertain", "damage_detected": False, "needs_human_review": True}])
def test_visual_gates(change):
    c, q, v, h = inputs()
    v = Member2Output.model_validate(v.model_dump() | change)
    assert recommend_handoff(verify_claim(c, q, v), h).decision == "Request Evidence"


@pytest.mark.parametrize("risk,decision", [(0.0, "Auto Refund"), (0.20, "Auto Refund"),
    (0.20001, "Manual Review"), (1.0, "Manual Review"), (None, "Manual Review")])
def test_risk_boundary(risk, decision):
    c, q, v, h = inputs()
    h.risk_score = risk
    assert recommend_handoff(verify_claim(c, q, v), h).decision == decision


@pytest.mark.parametrize("risk", [-0.1, 1.1, float("nan"), float("inf")])
def test_invalid_risk_rejected(risk):
    with pytest.raises(ValidationError):
        HandoffContext(case_id="x", risk_score=risk)


@pytest.mark.parametrize("field", ["order_valid", "policy_eligible", "image_order_verified"])
@pytest.mark.parametrize("value", [False, None])
def test_upstream_facts_required(field, value):
    c, q, v, h = inputs()
    setattr(h, field, value)
    assert recommend_handoff(verify_claim(c, q, v), h).decision == "Manual Review"


def test_high_risk_precedes_request_evidence():
    c, q, v, h = inputs()
    q.image_usable = False
    h.risk_score = 0.8
    assert recommend_handoff(verify_claim(c, q, v), h).decision == "Manual Review"


def test_missing_images_and_incomplete_evidence():
    c, q, v, h = inputs()
    h.evidence_complete = False
    assert recommend_handoff(verify_claim(c, q, v), h).decision == "Request Evidence"
    c.image_paths = []
    assert verify_claim(c, q, v).verdict == "ambiguous"


def test_case_ids_cannot_be_mixed():
    c, q, v, h = inputs()
    q.case_id = "another"
    with pytest.raises(ValueError, match="case_id"):
        verify_claim(c, q, v)
    q.case_id = c.case_id
    h.case_id = "another"
    with pytest.raises(ValueError, match="case_id"):
        recommend_handoff(verify_claim(c, q, v), h)


@pytest.mark.parametrize("threshold", [-1, 2, float("nan")])
def test_invalid_thresholds(threshold):
    c, q, v, h = inputs()
    with pytest.raises(ValueError):
        verify_claim(c, q, v, threshold)
    with pytest.raises(ValueError):
        recommend_handoff(verify_claim(c, q, v), h, threshold)


def rows():
    return [dict(case_id=str(i), source_image_id=str(i // 2), file_name=f"{i//2}.jpg",
                 damage_type="hole_or_tear", expected_verdict="positive",
                 construction_method="original_image_matching_claim", review_status="provisional_week1")
            for i in range(12)]


def test_sampling_keeps_source_groups_and_is_order_independent():
    manifest, audit = prepare(rows(), sample_groups=2)
    assert audit["sample_cases"] == 4
    assert prepare(list(reversed(rows())), 2) == (manifest, audit)
    for group in {r["source_image_id"] for r in manifest}:
        assert len({r["review_batch"] for r in manifest if r["source_image_id"] == group}) == 1
    assert all(r["benchmark_eligible"] == "false" for r in manifest)


@pytest.mark.parametrize("bad", [[], rows() + [rows()[0]], [rows()[0] | {"damage_type": "typo"}],
    [rows()[0] | {"source_image_id": ""}], [rows()[0] | {"expected_verdict": "typo"}]])
def test_invalid_dataset_fails(bad):
    with pytest.raises(ValueError):
        prepare(bad)


def test_clean_and_ambiguous_cases_flagged():
    data = rows()[:2]
    data[0]["damage_type"] = "none"
    data[1].update(damage_type="uncertain_hole_or_tear", expected_verdict="ambiguous")
    manifest, _ = prepare(data)
    assert "clean_label_conflicts" in manifest[0]["audit_flags"]
    assert manifest[0]["normalized_damage_type"] == "no_damage"
    assert "variant_not_materialized" in manifest[1]["audit_flags"]


def test_committed_review_manifest_integrity():
    path = Path(__file__).parents[1] / "data/member2/week3/review_manifest.csv"
    with path.open(encoding="utf-8", newline="") as handle:
        manifest = list(csv.DictReader(handle))
    assert len(manifest) == 100
    assert len({r["source_image_id"] for r in manifest}) == 70
    assert len({r["case_id"] for r in manifest}) == 100
    assert sum("clean_label_conflicts" in r["audit_flags"] for r in manifest) == 20
    assert sum("variant_not_materialized" in r["audit_flags"] for r in manifest) == 30


def test_json_fixture_executes_shared_contract():
    path = Path(__file__).parents[1] / "data/member2/week3/refund_001.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    output = run(payload)
    assert output["handoff"]["decision"] == payload["expected_decision"]
    assert output["handoff"]["advisory_only"] is True
