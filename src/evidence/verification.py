"""Evidence-chain verification for the Member 3 prototype."""

from datetime import date
from typing import Any

from src.evidence.models import OrderRecord, RetrievedPolicy, VerifiedEvidence
from src.evidence.order import retrieve_order
from src.evidence.rag import retrieve_best_policy


def _normalize_product(value: str) -> str:
    return "".join(character for character in value.lower() if character.isalnum())


def _image_order_match(detected_product: str, order: OrderRecord) -> float:
    detected = _normalize_product(detected_product)
    product = _normalize_product(order.product_name)
    category = _normalize_product(order.product_category)
    if detected == product:
        return 1.0
    if detected == category or category in detected or detected in product:
        return 0.8
    return 0.0


def _days_since_purchase(order: OrderRecord, request_date: str) -> int:
    return (date.fromisoformat(request_date) - date.fromisoformat(order.purchase_date)).days


def verify_case(case: dict[str, Any]) -> VerifiedEvidence:
    """Retrieve order/policy evidence and verify a single refund case."""

    order = retrieve_order(case["order_id"])
    if order is None:
        return VerifiedEvidence(
            case_id=case["case_id"],
            order_valid=False,
            image_order_match=0.0,
            policy_eligible=False,
            policy_match=0.0,
            evidence_completeness=round(_completeness(case, False, False), 2),
            refund_amount=0.0,
            reason="Order ID was not found.",
        )

    policy_query = " ".join(
        [
            order.product_category,
            case.get("damage_type", ""),
            case.get("claim_text", ""),
        ]
    )
    policy = retrieve_best_policy(policy_query)
    image_match = _image_order_match(case.get("detected_product", ""), order)
    eligible, reason = _policy_eligibility(case, order, policy, image_match)

    return VerifiedEvidence(
        case_id=case["case_id"],
        order_valid=True,
        image_order_match=image_match,
        policy_eligible=eligible,
        policy_match=policy.policy_match,
        evidence_completeness=round(_completeness(case, True, True), 2),
        refund_amount=order.price,
        policy_source=policy.policy_source,
        reason=reason,
    )


def _policy_eligibility(
    case: dict[str, Any],
    order: OrderRecord,
    policy: RetrievedPolicy,
    image_match: float,
) -> tuple[bool, str]:
    if order.status.lower() != "delivered":
        return False, "Order is not in delivered status."
    if order.final_sale:
        return False, "Final-sale products are not eligible for refund."
    if _days_since_purchase(order, case["request_date"]) < 0:
        return False, "Refund request date precedes purchase date."
    if _days_since_purchase(order, case["request_date"]) > policy.refund_window_days:
        return False, "Refund request is outside the policy window."
    if policy.requires_image and not case.get("image_present", False):
        return False, "Required image evidence is missing."
    if not case.get("damage_detected", False):
        return False, "No visible damage was detected."
    if case.get("damage_type", "").lower() not in policy.eligible_damage_types:
        return False, "Damage type is not covered by the retrieved policy."
    if image_match < 0.8:
        return False, "The detected product does not match the order."
    return True, "Order, image, and policy evidence are consistent."


def _completeness(case: dict[str, Any], has_order: bool, has_policy: bool) -> float:
    checks = (
        bool(case.get("claim_text")),
        bool(case.get("image_present")),
        bool(case.get("detected_product")),
        bool(case.get("damage_type")),
        bool(case.get("request_date")),
        has_order,
        has_policy,
    )
    return sum(checks) / len(checks)
