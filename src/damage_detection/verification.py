"""Claim-image verification for Member 2's structured visual evidence."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from src.common.schemas import CaseInput, Member1Output, Member2Output
from src.damage_detection.damage import DEFAULT_REVIEW_THRESHOLD


class VerificationResult(BaseModel):
    """Explain how the visual prediction supports the parsed claim."""

    member2: Member2Output
    verdict: Literal["positive", "negative", "ambiguous"]
    reason_code: str
    consistency_score: float | None = Field(default=None, ge=0.0, le=1.0)
    type_consistency: float | None = Field(default=None, ge=0.0, le=1.0)
    location_consistency: float | None = Field(default=None, ge=0.0, le=1.0)
    scope: str = "damage_type_and_optional_location"


DAMAGE_ALIASES = {
    "hole": "hole_or_tear",
    "tear": "hole_or_tear",
    "tear_hole": "hole_or_tear",
    "hole_or_tear": "hole_or_tear",
    "stain": "stain_or_spot",
    "spot": "stain_or_spot",
    "stain_or_spot": "stain_or_spot",
}

LOCATION_ALIASES = {
    "left sleeve": "left_sleeve",
    "left_sleeve": "left_sleeve",
    "right sleeve": "right_sleeve",
    "right_sleeve": "right_sleeve",
    "sleeve": "sleeve",
    "sleeves": "sleeve",
    "front": "front",
    "back": "back",
    "collar": "collar",
    "pocket": "pocket",
    "zipper": "zipper",
    "zip": "zipper",
    "hem": "hem",
    "waist": "waist",
    "waistband": "waist",
    "knee": "knee",
    "left knee": "left_knee",
    "left_knee": "left_knee",
    "right knee": "right_knee",
    "right_knee": "right_knee",
}


def normalize_location(value: str | None) -> str | None:
    """Map supported free-text garment regions to shared labels."""

    if value is None:
        return None
    normalized = " ".join(
        value.strip().lower().replace("-", " ").replace("_", " ").split()
    )
    return LOCATION_ALIASES.get(normalized)


def compare_location(
    claimed: str | None,
    detected: str | None,
) -> tuple[float | None, str]:
    """Compare garment regions without inventing a missing side or location."""

    if claimed is None:
        return None, "location_not_claimed"

    claimed_normalized = normalize_location(claimed)
    detected_normalized = normalize_location(detected)

    if claimed_normalized is None:
        return None, "unsupported_claimed_location"
    if detected_normalized is None:
        return None, "detected_location_missing_or_unsupported"
    if claimed_normalized == detected_normalized:
        return 1.0, "location_matches"
    if claimed_normalized == "sleeve" and detected_normalized in {
        "left_sleeve",
        "right_sleeve",
    }:
        return 1.0, "location_matches_general_region"
    if claimed_normalized == "knee" and detected_normalized in {
        "left_knee",
        "right_knee",
    }:
        return 1.0, "location_matches_general_region"
    if detected_normalized in {"sleeve", "knee"} and claimed_normalized.startswith(
        ("left_", "right_")
    ):
        return None, "detected_location_not_specific_enough"
    return 0.0, "location_mismatch"


def verify_claim(
    case: CaseInput,
    member1: Member1Output,
    visual: Member2Output,
    review_threshold: float = DEFAULT_REVIEW_THRESHOLD,
) -> VerificationResult:
    """Compare Member 1's parsed claim with Member 2's visual evidence.

    Product-to-order verification remains Member 3's responsibility. This function
    checks damage type and, when the customer claimed a location, damage location.
    It returns a copied Member2Output and never mutates the detector result.
    """

    if not 0.0 <= review_threshold <= 1.0:
        raise ValueError("review_threshold must be between 0 and 1")
    if len({case.case_id, member1.case_id, visual.case_id}) != 1:
        raise ValueError("CaseInput and member outputs have different case_id values.")

    visual = Member2Output.model_validate(visual.model_dump())
    claimed_defect = DAMAGE_ALIASES.get(
        (member1.claimed_defect or "").strip().lower()
    )

    verdict: Literal["positive", "negative", "ambiguous"] = "ambiguous"
    score = None
    type_score = None
    location_score = None
    reason = "unsupported_or_missing_claim"

    if not case.image_paths or not case.claim_text.strip():
        reason = "missing_case_evidence"
    elif (
        not member1.image_usable
        or not member1.relevant_region_visible
        or visual.evidence_quality != "good"
    ):
        reason = "insufficient_image_quality"
    elif (
        visual.needs_human_review
        or visual.damage_type == "uncertain"
        or visual.damage_confidence < review_threshold
    ):
        reason = "visual_review_required"
    elif claimed_defect is not None:
        if visual.damage_type == "no_damage":
            verdict = "negative"
            score = 0.0
            type_score = 0.0
            reason = "claimed_damage_not_detected"
        elif visual.damage_type != claimed_defect:
            verdict = "negative"
            score = 0.0
            type_score = 0.0
            reason = "damage_type_mismatch"
        else:
            type_score = 1.0
            location_score, location_reason = compare_location(
                member1.claimed_location,
                visual.damage_location,
            )
            if member1.claimed_location is None:
                verdict = "positive"
                score = 1.0
                reason = "damage_type_matches"
            elif location_score == 1.0:
                verdict = "positive"
                score = 1.0
                reason = "damage_type_and_location_match"
            elif location_score == 0.0:
                verdict = "negative"
                score = 0.0
                reason = location_reason
            else:
                reason = location_reason

    member2_payload = visual.model_dump()
    member2_payload.update(
        claim_image_consistency=score,
        needs_human_review=(visual.needs_human_review or verdict == "ambiguous"),
    )

    return VerificationResult(
        member2=Member2Output.model_validate(member2_payload),
        verdict=verdict,
        reason_code=reason,
        consistency_score=score,
        type_consistency=type_score,
        location_consistency=location_score,
    )
