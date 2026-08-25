"""Evidence-confidence rules for the Week 4 mock Agent."""

HIGH_CONFIDENCE_MIN = 0.80
MEDIUM_CONFIDENCE_MIN = 0.50


def calculate_evidence_confidence(member1, member2, member3):
    """Calculate a temporary mock confidence score.

    This is a Week 4 prototype, not the Week 6 ML model.
    """

    scores = [
        member1.image_quality,
        member2.damage_confidence,
        member2.claim_image_consistency,
        member3.image_order_consistency,
        member3.policy_match_score,
        member3.evidence_completeness,
    ]

    confidence = sum(scores) / len(scores)
    return round(confidence, 2)


def get_confidence_label(confidence):
    """Convert a numeric confidence score into HIGH, MEDIUM, or LOW."""

    if confidence >= HIGH_CONFIDENCE_MIN:
        return "HIGH"

    if confidence >= MEDIUM_CONFIDENCE_MIN:
        return "MEDIUM"

    return "LOW"

