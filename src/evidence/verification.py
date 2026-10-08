"""Evidence-chain verification for the Member 3 prototype."""

from datetime import date
from typing import Any

from src.evidence.models import OrderRecord, RetrievedPolicy, VerifiedEvidence
from src.evidence.order import retrieve_order
from src.evidence.rag import retrieve_best_policy
from src.damage_detection.product import ProductTypeClassifier


DAMAGE_TYPE_POLICY_ALIASES = {
    "hole_or_tear": {"hole_or_tear", "hole", "tear"},
    "stain_or_spot": {"stain_or_spot", "stain", "spot"},
}

MIN_PRODUCT_CONFIDENCE = ProductTypeClassifier.DEFAULT_MIN_CONFIDENCE

PRODUCT_ALIASES = {
    "coat": "jacket",
    "pants": "trousers",
    "tee": "tshirt",
    "jumper": "sweater",
    "pullover": "sweater",
}


def _normalize_product(value: str) -> str:
    normalized = "".join(
        character for character in value.lower() if character.isalnum()
    )
    return PRODUCT_ALIASES.get(normalized, normalized)


UNKNOWN_PRODUCTS = {'', 'unknown', 'notavailable', '未知', '不明'}


def _image_order_match(
    detected_product: str,
    order: OrderRecord,
    product_confidence: float | None = None,
) -> tuple[float, str]:
    detected = _normalize_product(detected_product or "")

    if detected in UNKNOWN_PRODUCTS:
        # Missing upstream product classification is not evidence of a
        # mismatch.  Use a neutral score while exposing an explicit status.
        return 0.5, "NOT_AVAILABLE"

    if (
        product_confidence is not None
        and product_confidence < MIN_PRODUCT_CONFIDENCE
    ):
        return 0.5, "NOT_AVAILABLE"

    product = _normalize_product(order.product_name)
    category = _normalize_product(order.product_category)

    if category in UNKNOWN_PRODUCTS:
        return 0.5, "NOT_AVAILABLE"

    if detected == product:
        return product_confidence if product_confidence is not None else 1.0, "MATCH"

    if (
        detected == category
        or category in detected
        or detected in product
    ):
        score = product_confidence if product_confidence is not None else 0.8
        return min(0.8, score), "MATCH"

    return 0.0, "MISMATCH"


def _days_since_delivery(order: OrderRecord, request_date: str) -> int:
    """Use delivery date for the policy window, with an explicit legacy fallback."""

    policy_start = order.delivery_date or order.purchase_date
    return (date.fromisoformat(request_date) - date.fromisoformat(policy_start)).days


def _damage_type_is_covered(damage_type: str, policy: RetrievedPolicy) -> bool:
    """Match canonical detector labels with legacy policy vocabulary."""

    normalized = damage_type.lower()
    accepted_labels = DAMAGE_TYPE_POLICY_ALIASES.get(normalized, {normalized})
    return bool(accepted_labels.intersection(policy.eligible_damage_types))


def verify_case(case: dict[str, Any], order_source=None) -> VerifiedEvidence:
    """Retrieve order/policy evidence and verify a single refund case."""

    order = (
        retrieve_order(case["order_id"], order_source)
        if order_source is not None
        else retrieve_order(case["order_id"])
    )
    if order is None:
        return VerifiedEvidence(
            case_id=case["case_id"],
            order_valid=False,
            image_order_match=0.0,
            image_order_match_status="NOT_AVAILABLE",
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
    policy = retrieve_best_policy(policy_query, retailer=order.retailer)
    image_match, image_match_status = _image_order_match(
        case.get("detected_product", ""),
        order,
        case.get("product_confidence"),
    )
    eligible, reason = _policy_eligibility(
        case, order, policy, image_match_status
    )

    return VerifiedEvidence(
        case_id=case["case_id"],
        order_valid=True,
        image_order_match=image_match,
        image_order_match_status=image_match_status,
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
    image_match_status: str,
) -> tuple[bool, str]:
    if order.status.lower() != "delivered":
        return False, "Order is not in delivered status."
    if order.final_sale:
        return False, (
            "Final-sale products are not eligible for automatic refund; "
            "statutory defect rights require manual review."
        )
    excluded = {_normalize_product(value) for value in policy.excluded_categories}
    if _normalize_product(order.product_category) in excluded:
        return False, "Product category is excluded by the retrieved return policy."
    if _days_since_delivery(order, case["request_date"]) < 0:
        return False, "Refund request date precedes delivery date."
    if _days_since_delivery(order, case["request_date"]) > policy.refund_window_days:
        return False, "Refund request is outside the policy window."
    if _normalize_product(order.product_category) in UNKNOWN_PRODUCTS:
        return False, "Order product category is unverified; review is required before automatic refund."
    if policy.requires_image and not case.get("image_present", False):
        return False, "Required image evidence is missing."
    if not case.get("image_usable", True):
        return False, "Submitted image evidence is not usable."
    if not case.get("damage_detected", False):
        return False, "No visible damage was detected."
    consistency = case.get("claim_image_consistency")
    if consistency is None:
        return False, "Claim-image consistency evidence is missing."
    if consistency < 0.5:
        return False, "Image evidence does not sufficiently support the claim."
    if not _damage_type_is_covered(case.get("damage_type", ""), policy):
        return False, "Damage type is not covered by the retrieved policy."
    if image_match_status == "MISMATCH":
        return False, "The detected product does not match the order."
    if image_match_status == "NOT_AVAILABLE":
        return True, (
            "Order and policy evidence are consistent; product type was not "
            "independently identified from the image."
        )
    return True, "Order, image, and policy evidence are consistent."


def _completeness(case: dict[str, Any], has_order: bool, has_policy: bool) -> float:
    checks = (
        bool(case.get("claim_text")),
        bool(case.get("image_present")),
        bool(case.get("detected_product")),
        bool(case.get("damage_type")),
        bool(case.get("request_date")),
        case.get("image_usable", True) is True,
        (
            case.get("claim_image_consistency") is not None
            and case["claim_image_consistency"] >= 0.5
        ),
        has_order,
        has_policy,
    )
    return sum(checks) / len(checks)
