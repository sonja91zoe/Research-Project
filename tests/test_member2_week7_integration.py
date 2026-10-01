"""Member 2 Week 7 integration tests using controlled visual predictions."""

from pathlib import Path

from src.agent.member2_adapter import run_member2, run_member2_verification
from src.common.schemas import CaseInput, Member1Output
from src.damage_detection.damage import DamageDetector, DamagePrediction, FixedBackend


def make_inputs(tmp_path: Path, *, claimed_defect="tear_hole", claimed_location=None):
    image_path = tmp_path / "garment.jpg"
    image_path.write_bytes(b"member2-week7-test-image")

    case = CaseInput(
        case_id="M2-W4-001",
        order_id="ORD001",
        claim_text="The jacket has a tear.",
        image_paths=[str(image_path)],
    )
    member1 = Member1Output(
        case_id=case.case_id,
        product="jacket",
        claimed_defect=claimed_defect,
        claimed_location=claimed_location,
        image_quality=0.95,
        blur_score=100.0,
        lighting_score=1.0,
        relevant_region_visible=True,
        image_usable=True,
    )
    return case, member1


def detector(damage_type, *, location=None, confidence=0.95):
    return DamageDetector(
        FixedBackend(
            DamagePrediction(
                damage_type,
                confidence,
                "Controlled visual prediction.",
                damage_location=location,
            )
        )
    )


def test_adapter_fills_claim_image_consistency(tmp_path):
    case, member1 = make_inputs(tmp_path)

    result = run_member2(
        case,
        member1,
        detector=detector("hole_or_tear"),
    )

    assert result.damage_type == "hole_or_tear"
    assert result.claim_image_consistency == 1.0
    assert result.needs_human_review is False


def test_parsed_product_does_not_block_damage_verification(tmp_path):
    case, member1 = make_inputs(tmp_path)

    result = run_member2_verification(
        case,
        member1,
        detector=detector("hole_or_tear"),
    )

    assert member1.product == "jacket"
    assert result.verdict == "positive"
    assert result.reason_code == "damage_type_matches"
    assert result.scope == "damage_type_and_optional_location"


def test_damage_type_mismatch_is_structured_negative(tmp_path):
    case, member1 = make_inputs(tmp_path)

    result = run_member2_verification(
        case,
        member1,
        detector=detector("stain_or_spot"),
    )

    assert result.verdict == "negative"
    assert result.consistency_score == 0.0
    assert result.reason_code == "damage_type_mismatch"
    assert result.member2.needs_human_review is False


def test_claimed_location_requires_visual_location(tmp_path):
    case, member1 = make_inputs(tmp_path, claimed_location="left_sleeve")

    missing = run_member2_verification(
        case,
        member1,
        detector=detector("hole_or_tear"),
    )
    matching = run_member2_verification(
        case,
        member1,
        detector=detector("hole_or_tear", location="left_sleeve"),
    )

    assert missing.verdict == "ambiguous"
    assert missing.member2.claim_image_consistency is None
    assert missing.member2.needs_human_review is True
    assert matching.verdict == "positive"
    assert matching.location_consistency == 1.0


def test_unusable_member1_evidence_bypasses_automatic_verification(tmp_path):
    case, member1 = make_inputs(tmp_path)
    member1.image_usable = False

    result = run_member2_verification(
        case,
        member1,
        detector=detector("hole_or_tear"),
    )

    assert result.verdict == "ambiguous"
    assert result.reason_code == "insufficient_image_quality"
    assert result.member2.damage_type == "uncertain"
    assert result.member2.needs_human_review is True
