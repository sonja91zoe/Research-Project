"""Structured records exchanged by the Member 3 evidence modules."""

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class OrderRecord:
    order_id: str
    product_name: str
    product_category: str
    price: float
    purchase_date: str
    status: str
    final_sale: bool = False
    delivery_date: Optional[str] = None
    data_type: str = "synthetic_order"
    image_evidence: Optional[dict[str, Any]] = None
    retailer: str = "H&M Australia"
    catalog_version: Optional[str] = None
    photo_pairing: Optional[dict[str, Any]] = None


@dataclass(frozen=True)
class RetrievedPolicy:
    policy_id: str
    title: str
    policy_text: str
    policy_source: str
    policy_match: float
    refund_window_days: int
    requires_image: bool
    eligible_damage_types: tuple[str, ...]
    policy_kind: str = "retailer_policy"
    source_url: Optional[str] = None
    source_updated_date: Optional[str] = None
    retrieved_date: Optional[str] = None
    excluded_categories: tuple[str, ...] = ()
    return_fee_aud: Optional[float] = None
    retailer: str = "H&M Australia"


@dataclass(frozen=True)
class VerifiedEvidence:
    case_id: str
    order_valid: bool
    image_order_match: float
    image_order_match_status: str
    policy_eligible: bool
    policy_match: float
    evidence_completeness: float
    refund_amount: float
    policy_source: Optional[str] = None
    reason: Optional[str] = None


@dataclass(frozen=True)
class EvidenceChain:
    """Traceable inputs, retrieval results, and Member 3 output for one case."""

    case_id: str
    claim: dict[str, Any]
    image_evidence: dict[str, Any]
    order_evidence: Optional[OrderRecord]
    policy_evidence: Optional[RetrievedPolicy]
    verified_evidence: VerifiedEvidence
    member3_output: dict[str, Any]
