"""Rule-based refund decision engine for Student 4 Week 5."""

from src.damage_detection.damage import MIN_USABLE_DAMAGE_CONFIDENCE

MIN_CLAIM_IMAGE_CONSISTENCY = 0.50

DECISION_MATRIX = {
    ("HIGH", "LOW"): "AUTO_REFUND",
    ("HIGH", "MEDIUM"): "HUMAN_REVIEW",
    ("HIGH", "HIGH"): "HUMAN_REVIEW",
    ("MEDIUM", "LOW"): "REQUEST_MORE_EVIDENCE",
    ("MEDIUM", "MEDIUM"): "HUMAN_REVIEW",
    ("MEDIUM", "HIGH"): "HUMAN_REVIEW",
    ("LOW", "LOW"): "REQUEST_MORE_EVIDENCE",
    ("LOW", "MEDIUM"): "REQUEST_MORE_EVIDENCE",
    ("LOW", "HIGH"): "HUMAN_REVIEW",
}


def make_decision(
    confidence_label,
    refund_risk,
    member1,
    member2,
    member3,
):
    """Apply override rules first, then use the decision matrix."""

    if not member1.image_usable:
        return (
            "REQUEST_MORE_EVIDENCE",
            "The uploaded image is not usable.",
        )

    if not member1.relevant_region_visible:
        return (
            "REQUEST_MORE_EVIDENCE",
            "The relevant product region is not visible.",
        )

    if not member3.order_valid:
        return (
            "HUMAN_REVIEW",
            "The order could not be validated.",
        )

    if member3.image_order_match_status == "MISMATCH":
        return (
            "HUMAN_REVIEW",
            "The detected product does not match the selected order.",
        )

    # No usable damage evidence should request more evidence
    # before policy eligibility routes the case to human review.
    if not member2.damage_detected:
        return (
            "REQUEST_MORE_EVIDENCE",
            "The submitted image does not show detectable damage.",
        )

    if (
        member2.damage_detected
        and member2.damage_confidence < MIN_USABLE_DAMAGE_CONFIDENCE
    ):
        return (
            "REQUEST_MORE_EVIDENCE",
            "Damage confidence is below the minimum usable threshold; "
            "submit a clearer close-up photo.",
        )

    if not member3.policy_eligible:
        return (
            "HUMAN_REVIEW",
            "Refund-policy eligibility is not confirmed.",
        )

    if member2.evidence_quality in {"poor", "unusable"}:
        return (
            "REQUEST_MORE_EVIDENCE",
            "The damage module reports insufficient image evidence.",
        )

    if member2.needs_human_review:
        return (
            "HUMAN_REVIEW",
            "The damage module requires human review.",
        )

    if member2.claim_image_consistency is None:
        return (
            "REQUEST_MORE_EVIDENCE",
            "Claim-image consistency evidence is missing.",
        )

    if (
        member2.claim_image_consistency
        < MIN_CLAIM_IMAGE_CONSISTENCY
    ):
        return (
            "REQUEST_MORE_EVIDENCE",
            "The image does not sufficiently support "
            "the customer claim.",
        )

    matrix_key = (confidence_label, refund_risk)

    if matrix_key not in DECISION_MATRIX:
        raise ValueError(
            "Unsupported confidence and risk combination: "
            f"{matrix_key}."
        )

    decision = DECISION_MATRIX[matrix_key]

    if (
        member3.image_order_match_status == "NOT_AVAILABLE"
        and decision == "AUTO_REFUND"
    ):
        return (
            "REQUEST_MORE_EVIDENCE",
            "Product type could not be verified against the selected order; "
            "provide a clearer image of the item.",
        )

    reason = (
        "Decision matrix result: "
        f"confidence={confidence_label}, "
        f"refund risk={refund_risk}."
    )

    if member3.image_order_match_status == "NOT_AVAILABLE":
        reason += (
            " Product type was not independently identified; the neutral "
            "image-order score was included in evidence confidence."
        )

    return decision, reason