"""Member 2 Week 3: conservative claim-type verification, no refund execution."""
from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from src.common.schemas import CaseInput, Member1Output, Member2Output


class HandoffContext(BaseModel):
    """Explicit upstream facts; missing values never qualify for automation."""
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True)
    case_id: str
    risk_score: float | None = Field(default=None, ge=0, le=1)
    order_valid: bool | None = None
    policy_eligible: bool | None = None
    evidence_complete: bool | None = None
    image_order_verified: bool | None = None


class VerificationResult(BaseModel):
    member2: Member2Output
    verdict: Literal["positive", "negative", "ambiguous"]
    reason_code: str
    # A rule score, not a calibrated probability or visual severity estimate.
    consistency_score: float | None = Field(default=None, ge=0, le=1)
    type_consistency: float | None = Field(default=None, ge=0, le=1)
    location_consistency: float | None = Field(default=None, ge=0, le=1)
    scope: str = "damage_type_only"


class HandoffResult(BaseModel):
    case_id: str
    decision: Literal["Auto Refund", "Request Evidence", "Manual Review"]
    reason_code: str
    advisory_only: bool = True


ALIASES = {
    "hole": "hole_or_tear", "tear": "hole_or_tear", "tear_hole": "hole_or_tear",
    "hole_or_tear": "hole_or_tear", "stain": "stain_or_spot",
    "spot": "stain_or_spot", "stain_or_spot": "stain_or_spot",
}

LOCATION_ALIASES = {
    "left sleeve": "left_sleeve", "left_sleeve": "left_sleeve",
    "right sleeve": "right_sleeve", "right_sleeve": "right_sleeve",
    "sleeve": "sleeve", "sleeves": "sleeve", "front": "front",
    "back": "back", "collar": "collar", "pocket": "pocket",
    "zipper": "zipper", "zip": "zipper", "hem": "hem",
    "waist": "waist", "waistband": "waist", "knee": "knee",
    "left knee": "left_knee", "left_knee": "left_knee",
    "right knee": "right_knee", "right_knee": "right_knee",
}


def normalize_location(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.strip().lower().replace("-", " ").replace("_", " ").split())
    return LOCATION_ALIASES.get(normalized)


def compare_location(claimed: str | None, detected: str | None) -> tuple[float | None, str]:
    """Compare supported garment regions without guessing an unreported side."""
    if claimed is None:
        return None, "location_not_claimed"
    claimed_norm, detected_norm = normalize_location(claimed), normalize_location(detected)
    if claimed_norm is None:
        return None, "unsupported_claimed_location"
    if detected_norm is None:
        return None, "detected_location_missing_or_unsupported"
    if claimed_norm == detected_norm:
        return 1.0, "location_matches"
    # A general claim is supported by a more specific detected subregion.
    if claimed_norm == "sleeve" and detected_norm in {"left_sleeve", "right_sleeve"}:
        return 1.0, "location_matches_general_region"
    if claimed_norm == "knee" and detected_norm in {"left_knee", "right_knee"}:
        return 1.0, "location_matches_general_region"
    # A specific claim cannot be confirmed by a detector that reports only a side-free region.
    if detected_norm in {"sleeve", "knee"} and claimed_norm.startswith(("left_", "right_")):
        return None, "detected_location_not_specific_enough"
    return 0.0, "location_mismatch"


def verify_claim(case: CaseInput, quality: Member1Output, visual: Member2Output,
                 review_threshold: float = 0.70) -> VerificationResult:
    """Use Member1's extracted defect; never infer it from benchmark verdicts.

    Product/location assertions require independent verification, so this baseline
    abstains when they are present. It preserves the original detector output.
    """
    if not 0 <= review_threshold <= 1:
        raise ValueError("review_threshold must be between 0 and 1")
    if len({case.case_id, quality.case_id, visual.case_id}) != 1:
        raise ValueError("case_id mismatch")
    # Revalidate copies because upstream Pydantic model_copy can bypass validation.
    visual = Member2Output.model_validate(visual.model_dump())
    defect = ALIASES.get((quality.claimed_defect or "").strip().lower())
    verdict, score, type_score, location_score = "ambiguous", None, None, None
    reason = "unsupported_or_missing_claim"
    if not case.image_paths or not case.claim_text.strip():
        reason = "missing_case_evidence"
    elif not quality.image_usable or not quality.relevant_region_visible or visual.evidence_quality != "good":
        reason = "insufficient_image_quality"
    elif visual.needs_human_review or visual.damage_type == "uncertain" or visual.damage_confidence < review_threshold:
        reason = "visual_review_required"
    elif quality.product:
        reason = "product_not_verified"
    elif defect is not None:
        if visual.damage_type == "no_damage":
            reason = "clean_controls_not_validated"
        elif visual.damage_type == defect:
            type_score = 1.0
            location_score, location_reason = compare_location(
                quality.claimed_location, visual.damage_location)
            if quality.claimed_location is None:
                verdict, score, reason = "positive", 1.0, "damage_type_matches"
            elif location_score == 1.0:
                verdict, score, reason = "positive", 1.0, "damage_type_and_location_match"
            elif location_score == 0.0:
                verdict, score, reason = "negative", 0.0, location_reason
            else:
                reason = location_reason
        else:
            verdict, score, type_score, reason = "negative", 0.0, 0.0, "damage_type_mismatch"
    payload = visual.model_dump()
    payload.update(claim_image_consistency=score,
                   needs_human_review=visual.needs_human_review or verdict != "positive")
    return VerificationResult(member2=Member2Output.model_validate(payload),
                              verdict=verdict, consistency_score=score,
                              type_consistency=type_score,
                              location_consistency=location_score,
                              reason_code=reason)


def recommend_handoff(result: VerificationResult, context: HandoffContext,
                      max_auto_risk: float = 0.20) -> HandoffResult:
    """Member2 integration example; does not call or replace Member4's module."""
    if not 0 <= max_auto_risk <= 1:
        raise ValueError("max_auto_risk must be between 0 and 1")
    context = HandoffContext.model_validate(context.model_dump())
    if result.member2.case_id != context.case_id:
        raise ValueError("case_id mismatch")
    decision, reason = "Manual Review", "upstream_verification_missing"
    if context.risk_score is not None and context.risk_score > max_auto_risk:
        reason = "risk_above_auto_threshold"
    elif context.order_valid is False or context.policy_eligible is False or context.image_order_verified is False:
        reason = "upstream_verification_failed"
    elif result.verdict == "negative":
        reason = "claim_image_mismatch"
    elif result.verdict == "ambiguous":
        decision, reason = "Request Evidence", result.reason_code
    elif context.evidence_complete is False:
        decision, reason = "Request Evidence", "incomplete_evidence"
    elif (context.risk_score is not None
          and all(x is True for x in (context.order_valid, context.policy_eligible,
                                     context.image_order_verified, context.evidence_complete))
          and result.consistency_score == 1.0
          and result.member2.claim_image_consistency == 1.0
          and result.member2.damage_type in {"hole_or_tear", "stain_or_spot"}
          and result.member2.evidence_quality == "good"
          and not result.member2.needs_human_review):
        decision, reason = "Auto Refund", "verified_type_and_low_risk"
    return HandoffResult(case_id=context.case_id, decision=decision, reason_code=reason)
