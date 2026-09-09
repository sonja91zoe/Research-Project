"""Student 4 Week 6 ML Evidence Confidence V1."""

from pathlib import Path

import joblib
import numpy as np
import pandas as pd


MODEL_PATH = Path(
    "models/student4_evidence_confidence_v1.joblib"
)

FEATURES = [
    "image_quality",
    "damage_confidence",
    "claim_image_consistency",
    "image_order_consistency",
    "policy_match_score",
    "evidence_completeness",
    "image_usable",
    "relevant_region_visible",
    "damage_detected",
    "damage_evidence_quality",
    "damage_needs_human_review",
    "order_valid",
    "policy_eligible",
]

EVIDENCE_QUALITY_SCORE = {
    "good": 1.0,
    "poor": 0.5,
    "unusable": 0.0,
}


def build_feature_row(
    member1,
    member2,
    member3,
):
    """Convert Members 1-3 outputs into one model input row."""

    claim_consistency = (
        member2.claim_image_consistency
    )

    if claim_consistency is None:
        claim_consistency = np.nan

    row = {
        "image_quality": (
            member1.image_quality
        ),
        "damage_confidence": (
            member2.damage_confidence
        ),
        "claim_image_consistency": (
            claim_consistency
        ),
        "image_order_consistency": (
            member3.image_order_consistency
        ),
        "policy_match_score": (
            member3.policy_match_score
        ),
        "evidence_completeness": (
            member3.evidence_completeness
        ),
        "image_usable": int(
            member1.image_usable
        ),
        "relevant_region_visible": int(
            member1.relevant_region_visible
        ),
        "damage_detected": int(
            member2.damage_detected
        ),
        "damage_evidence_quality": (
            EVIDENCE_QUALITY_SCORE[
                member2.evidence_quality
            ]
        ),
        "damage_needs_human_review": int(
            member2.needs_human_review
        ),
        "order_valid": int(
            member3.order_valid
        ),
        "policy_eligible": int(
            member3.policy_eligible
        ),
    }

    return pd.DataFrame(
        [row],
        columns=FEATURES,
    )


def predict_evidence_confidence(
    member1,
    member2,
    member3,
    model=None,
):
    """Return the probability that the evidence is reliable."""

    if model is None:
        model = joblib.load(MODEL_PATH)

    feature_row = build_feature_row(
        member1,
        member2,
        member3,
    )

    positive_class_index = list(
        model.classes_
    ).index(1)

    probability = model.predict_proba(
        feature_row
    )[0, positive_class_index]

    return round(
        float(probability),
        2,
    )