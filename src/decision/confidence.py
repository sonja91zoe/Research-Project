"""Rule-based evidence-confidence baseline for Student 4 Week 5."""

HIGH_CONFIDENCE_MIN = 0.80
MEDIUM_CONFIDENCE_MIN = 0.50

FEATURE_WEIGHTS = {
    "image_quality": 0.15,
    "damage_confidence": 0.20,
    "claim_image_consistency": 0.20,
    "image_order_consistency": 0.15,
    "policy_match_score": 0.15,
    "evidence_completeness": 0.15,
}


def _validate_score(name, value):
    """Ensure that an evidence score is between 0 and 1."""

    if not 0.0 <= value <= 1.0:
        raise ValueError(
            f"{name} must be between 0 and 1, "
            f"but received {value}."
        )


def calculate_evidence_confidence(member1, member2, member3):
    """Combine evidence features into a weighted confidence score."""

    feature_values = {
        "image_quality": member1.image_quality,
        "damage_confidence": member2.damage_confidence,
        "claim_image_consistency": (
            member2.claim_image_consistency
        ),
        "image_order_consistency": (
            member3.image_order_consistency
        ),
        "policy_match_score": member3.policy_match_score,
        "evidence_completeness": (
            member3.evidence_completeness
        ),
    }

    for name, value in feature_values.items():
        _validate_score(name, value)

    confidence = sum(
        feature_values[name] * FEATURE_WEIGHTS[name]
        for name in FEATURE_WEIGHTS
    )

    return round(confidence, 2)


def get_confidence_label(confidence):
    """Convert a confidence score into HIGH, MEDIUM, or LOW."""

    _validate_score("confidence", confidence)

    if confidence >= HIGH_CONFIDENCE_MIN:
        return "HIGH"

    if confidence >= MEDIUM_CONFIDENCE_MIN:
        return "MEDIUM"

    return "LOW"

