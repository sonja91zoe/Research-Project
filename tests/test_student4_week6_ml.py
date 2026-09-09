import json

import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.common.schemas import (
    Member1Output,
    Member2Output,
    Member3Output,
)
from src.decision.ml_confidence import (
    FEATURES,
    build_feature_row,
    predict_evidence_confidence,
)


def load_case():
    """Load the existing Student 4 test case."""

    with open(
        "data/test_cases/student4_auto_refund.json",
        encoding="utf-8",
    ) as case_file:
        raw = json.load(case_file)

    member1 = Member1Output(
        **raw["member1"]
    )
    member2 = Member2Output(
        **raw["member2"]
    )
    member3 = Member3Output(
        **raw["member3"]
    )

    return member1, member2, member3


def make_tiny_model():
    """Create a small model used only by the tests."""

    low_confidence = (
        [0.2] * 6
        + [0, 0, 0, 0.0, 1, 0, 0]
    )

    high_confidence = (
        [0.9] * 6
        + [1, 1, 1, 1.0, 0, 1, 1]
    )

    training_rows = pd.DataFrame(
        [
            low_confidence,
            high_confidence,
            low_confidence,
            high_confidence,
        ],
        columns=FEATURES,
    )

    model = Pipeline(
        [
            (
                "imputer",
                SimpleImputer(
                    strategy="median"
                ),
            ),
            (
                "scaler",
                StandardScaler(),
            ),
            (
                "model",
                LogisticRegression(),
            ),
        ]
    )

    return model.fit(
        training_rows,
        [0, 1, 0, 1],
    )


def test_feature_row_matches_shared_schema():
    """The three member outputs should become 13 features."""

    feature_row = build_feature_row(
        *load_case()
    )

    assert feature_row.shape == (1, 13)

    assert (
        feature_row.loc[
            0,
            "damage_evidence_quality",
        ]
        == 1.0
    )

    assert (
        feature_row.loc[
            0,
            "damage_needs_human_review",
        ]
        == 0
    )


def test_prediction_is_between_zero_and_one():
    """The returned confidence must be a probability."""

    confidence = predict_evidence_confidence(
        *load_case(),
        model=make_tiny_model(),
    )

    assert 0.0 <= confidence <= 1.0


def test_missing_claim_consistency_does_not_crash():
    """The model should accept an optional missing value."""

    member1, member2, member3 = load_case()

    member2.claim_image_consistency = None

    confidence = predict_evidence_confidence(
        member1,
        member2,
        member3,
        model=make_tiny_model(),
    )

    assert 0.0 <= confidence <= 1.0


def test_saved_week6_model_can_predict():
    """The actual saved Week 6 model should work."""

    confidence = predict_evidence_confidence(
        *load_case()
    )

    assert 0.0 <= confidence <= 1.0