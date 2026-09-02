"""Rule-based refund decision engine for Student 4 Week 5."""

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

    if not member3.policy_eligible:
        return (
            "HUMAN_REVIEW",
            "Refund-policy eligibility is not confirmed.",
        )

    if not member2.damage_detected:
        return (
            "REQUEST_MORE_EVIDENCE",
            "The submitted image does not show detectable damage.",
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

    reason = (
        "Decision matrix result: "
        f"confidence={confidence_label}, "
        f"refund risk={refund_risk}."
    )

    return decision, reason