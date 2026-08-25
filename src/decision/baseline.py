"""Week 5 rule-based confidence and refund-decision baseline."""

from dataclasses import dataclass

from src.common.schemas import EvidenceFeatures
from src.decision.confidence import get_confidence_label
from src.decision.risk import calculate_refund_risk


DECISION_MATRIX = {
    ("HIGH", "LOW"): "AUTO_REFUND",
    ("HIGH", "MEDIUM"): "AUTO_REFUND",
    ("HIGH", "HIGH"): "HUMAN_REVIEW",
    ("MEDIUM", "LOW"): "REQUEST_MORE_EVIDENCE",
    ("MEDIUM", "MEDIUM"): "HUMAN_REVIEW",
    ("MEDIUM", "HIGH"): "HUMAN_REVIEW",
    ("LOW", "LOW"): "REQUEST_MORE_EVIDENCE",
    ("LOW", "MEDIUM"): "REQUEST_MORE_EVIDENCE",
    ("LOW", "HIGH"): "HUMAN_REVIEW",
}


@dataclass(frozen=True)
class BaselineDecision:
    evidence_confidence: float
    confidence_label: str
    refund_risk: str
    decision: str
    reason: str


def calculate_feature_confidence(features: EvidenceFeatures) -> float:
    """Calculate an equally weighted confidence score from six signals."""

    scores = (
        features.image_quality,
        features.damage_confidence,
        features.claim_image_consistency,
        features.image_order_match,
        features.evidence_completeness,
        features.policy_match,
    )

    if any(isinstance(score, bool) or not isinstance(score, (int, float)) for score in scores):
        raise TypeError("evidence confidence features must be numeric")

    if any(not 0.0 <= score <= 1.0 for score in scores):
        raise ValueError("evidence confidence features must be between 0 and 1")

    return round(sum(scores) / len(scores), 2)


def make_baseline_decision(features: EvidenceFeatures) -> BaselineDecision:
    """Apply eligibility safeguards, refund risk, and the decision matrix."""

    confidence = calculate_feature_confidence(features)
    confidence_label = get_confidence_label(confidence)
    refund_risk = calculate_refund_risk(features.refund_amount)

    if not features.policy_eligible:
        decision = "HUMAN_REVIEW"
        reason = "Refund-policy eligibility is not confirmed."
    else:
        decision = DECISION_MATRIX[(confidence_label, refund_risk)]
        reason = (
            "Rule-based baseline: "
            f"confidence={confidence_label} ({confidence:.2f}), "
            f"refund risk={refund_risk}."
        )

    return BaselineDecision(
        evidence_confidence=confidence,
        confidence_label=confidence_label,
        refund_risk=refund_risk,
        decision=decision,
        reason=reason,
    )
