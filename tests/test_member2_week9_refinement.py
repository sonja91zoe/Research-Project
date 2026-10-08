"""Regression tests for the final Member 2 visual-verification contract."""

from src.common.schemas import CaseInput, Member1Output, Member2Output
from src.damage_detection.verification import verify_claim


def make_case_and_claim(*, defect: str = "tear_hole", location: str | None = None):
    case = CaseInput(
        case_id="M2-W9-001",
        order_id="EVAL-ORDER",
        claim_text="The garment has a tear.",
        image_paths=["data/member2/week1/images/holes_35/hole_001.jpg"],
    )
    claim = Member1Output(
        case_id=case.case_id,
        claimed_defect=defect,
        claimed_location=location,
        image_quality=1.0,
        blur_score=0.0,
        lighting_score=1.0,
        relevant_region_visible=True,
        image_usable=True,
    )
    return case, claim


def make_visual(damage_type: str, *, confidence: float = 0.9, location: str | None = None):
    return Member2Output(
        case_id="M2-W9-001",
        damage_detected=damage_type in {"hole_or_tear", "stain_or_spot"},
        damage_type=damage_type,
        damage_location=location,
        damage_confidence=confidence,
        needs_human_review=damage_type == "uncertain",
    )


def test_matching_visual_damage_is_supported():
    case, claim = make_case_and_claim()
    result = verify_claim(case, claim, make_visual("hole_or_tear"))
    assert result.verdict == "positive"
    assert result.consistency_score == 1.0
    assert result.member2.claim_image_consistency == 1.0
    assert result.member2.needs_human_review is False


def test_concrete_damage_mismatch_is_negative_not_review():
    case, claim = make_case_and_claim()
    result = verify_claim(case, claim, make_visual("stain_or_spot"))
    assert result.verdict == "negative"
    assert result.reason_code == "damage_type_mismatch"
    assert result.member2.claim_image_consistency == 0.0
    assert result.member2.needs_human_review is False


def test_low_confidence_evidence_stays_ambiguous():
    case, claim = make_case_and_claim()
    result = verify_claim(case, claim, make_visual("hole_or_tear", confidence=0.14))
    assert result.verdict == "ambiguous"
    assert result.reason_code == "visual_review_required"
    assert result.member2.claim_image_consistency is None
    assert result.member2.needs_human_review is True


def test_provisional_threshold_allows_claim_comparison_at_point_fifteen():
    case, claim = make_case_and_claim()
    result = verify_claim(case, claim, make_visual("hole_or_tear", confidence=0.15))
    assert result.verdict == "positive"
    assert result.consistency_score == 1.0
    assert result.member2.needs_human_review is False


def test_location_specific_claim_needs_location_evidence():
    case, claim = make_case_and_claim(location="left sleeve")
    result = verify_claim(case, claim, make_visual("hole_or_tear"))
    assert result.verdict == "ambiguous"
    assert result.reason_code == "detected_location_missing_or_unsupported"
    assert result.member2.needs_human_review is True
