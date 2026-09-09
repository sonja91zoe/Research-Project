from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class CaseInput(BaseModel):
    case_id: str
    order_id: str
    claim_text: str
    image_paths: list[str]
class Member1Output(BaseModel):
    case_id: str

    product: str | None = None
    claimed_defect: str | None = None
    claimed_location: str | None = None

    image_quality: float
    blur_score: float
    lighting_score: float

    relevant_region_visible: bool
    image_usable: bool
class Member2Output(BaseModel):
    case_id: str

    detected_product: str | None = None

    damage_detected: bool
    damage_type: Literal[
        "hole_or_tear", "stain_or_spot", "no_damage", "uncertain"
    ]
    damage_location: str | None = None

    damage_confidence: float = Field(ge=0.0, le=1.0)
    evidence_quality: Literal["good", "poor", "unusable"] = "good"
    needs_human_review: bool = False
    rationale: str = ""
    model_version: str = "damage-detection-v1"

    # Reserved for Week 3. Optional keeps older integrations compatible without
    # making claim/image verification part of the Week 2 detector.
    claim_image_consistency: float | None = Field(default=None, ge=0.0, le=1.0)

    @field_validator("damage_type", mode="before")
    @classmethod
    def normalize_legacy_damage_type(cls, value):
        aliases = {
            "tear": "hole_or_tear",
            "hole": "hole_or_tear",
            "tear_hole": "hole_or_tear",
            "stain": "stain_or_spot",
            "spot": "stain_or_spot",
        }
        return aliases.get(value, value)

    @model_validator(mode="after")
    def validate_damage_state(self):
        concrete = {"hole_or_tear", "stain_or_spot"}
        if self.damage_type in concrete and not self.damage_detected:
            raise ValueError("a concrete damage type requires damage_detected=True")
        if self.damage_type == "no_damage" and self.damage_detected:
            raise ValueError("no_damage requires damage_detected=False")
        if self.damage_type == "uncertain" and not self.needs_human_review:
            raise ValueError("uncertain evidence requires human review")
        return self
class Member3Output(BaseModel):
    case_id: str

    order_valid: bool

    image_order_consistency: float

    policy_eligible: bool
    policy_match_score: float

    evidence_completeness: float

    refund_amount: float

    policy_source: str | None = None
class Member4Output(BaseModel):
    case_id: str

    evidence_confidence: float

    refund_risk: str

    decision: str

    reason: str
