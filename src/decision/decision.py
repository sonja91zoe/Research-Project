"""Decision matrix for the Week 4 mock Agent."""

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


def make_decision(confidence_label, refund_risk, member1, member2, member3):
    """Apply override rules first, then use the decision matrix."""

    if not member1.image_usable:
        return "REQUEST_MORE_EVIDENCE", "The uploaded image is not usable."

    if not member1.relevant_region_visible:
        return (
            "REQUEST_MORE_EVIDENCE",
            "The relevant product region is not visible.",
        )

    if not member3.order_valid:
        return "HUMAN_REVIEW", "The order could not be validated."

    if not member3.policy_eligible:
        return "HUMAN_REVIEW", "Refund-policy eligibility is not confirmed."

    if not member2.damage_detected:
        return (
            "REQUEST_MORE_EVIDENCE",
            "The submitted image does not show detectable damage.",
        )

    if member2.claim_image_consistency < 0.50:
        return (
            "REQUEST_MORE_EVIDENCE",
            "The image does not sufficiently support the customer claim.",
        )

    decision = DECISION_MATRIX[(confidence_label, refund_risk)]
    reason = (
        f"Decision matrix result: confidence={confidence_label}, "
        f"refund risk={refund_risk}."
    )

    return decision, reason

