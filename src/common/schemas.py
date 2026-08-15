from pydantic import BaseModel


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
    damage_type: str
    damage_location: str | None = None

    damage_confidence: float
    claim_image_consistency: float
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