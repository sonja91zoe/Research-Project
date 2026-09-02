"""Structured records exchanged by the Member 3 evidence modules."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class OrderRecord:
    order_id: str
    product_name: str
    product_category: str
    price: float
    purchase_date: str
    status: str
    final_sale: bool = False


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


@dataclass(frozen=True)
class VerifiedEvidence:
    case_id: str
    order_valid: bool
    image_order_match: float
    policy_eligible: bool
    policy_match: float
    evidence_completeness: float
    refund_amount: float
    policy_source: Optional[str] = None
    reason: Optional[str] = None
