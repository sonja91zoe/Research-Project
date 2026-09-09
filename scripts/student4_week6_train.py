"""Train and compare Student 4 Week 6 confidence methods."""

import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.decision.ml_confidence import FEATURES


DATA_PATH = Path(
    "data/member4/evidence_confidence_training_v1.csv"
)

MODEL_DIR = Path("models")

RESULTS_PATH = Path(
    "docs/student4_week6_metrics.json"
)

TARGET = "evidence_reliable"

RULE_SCORE_FEATURES = [
    "image_quality",
    "damage_confidence",
    "claim_image_consistency",
    "image_order_consistency",
    "policy_match_score",
    "evidence_completeness",
]


def evaluate(
    y_true,
    predictions,
    probabilities,
):
    """Calculate evaluation metrics for one method."""

    matrix = confusion_matrix(
        y_true,
        predictions,
        labels=[0, 1],
    )

    return {
        "accuracy": round(
            accuracy_score(
                y_true,
                predictions,
            ),
            3,
        ),
        "precision": round(
            precision_score(
                y_true,
                predictions,
                zero_division=0,
            ),
            3,
        ),
        "recall": round(
            recall_score(
                y_true,
                predictions,
                zero_division=0,
            ),
            3,
        ),
        "f1": round(
            f1_score(
                y_true,
                predictions,
                zero_division=0,
            ),
            3,
        ),
        "roc_auc": round(
            roc_auc_score(
                y_true,
                probabilities,
            ),
            3,
        ),
        "confusion_matrix": (
            matrix.tolist()
        ),
    }


def main():
    """Train, compare and save the Week 6 models."""

    data = pd.read_csv(DATA_PATH)

    X = data[FEATURES]
    y = data[TARGET]

    (
        X_train,
        X_remaining,
        y_train,
        y_remaining,
    ) = train_test_split(
        X,
        y,
        test_size=0.40,
        random_state=42,
        stratify=y,
    )

    (
        X_validation,
        X_test,
        y_validation,
        y_test,
    ) = train_test_split(
        X_remaining,
        y_remaining,
        test_size=0.50,
        random_state=42,
        stratify=y_remaining,
    )

    logistic_regression = Pipeline(
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
                LogisticRegression(
                    max_iter=1000,
                    class_weight="balanced",
                    random_state=42,
                ),
            ),
        ]
    )

    random_forest = Pipeline(
        [
            (
                "imputer",
                SimpleImputer(
                    strategy="median"
                ),
            ),
            (
                "model",
                RandomForestClassifier(
                    n_estimators=200,
                    max_depth=6,
                    min_samples_leaf=2,
                    class_weight="balanced",
                    random_state=42,
                ),
            ),
        ]
    )

    logistic_regression.fit(
        X_train,
        y_train,
    )

    random_forest.fit(
        X_train,
        y_train,
    )

    validation_rule_probability = (
        X_validation[
            RULE_SCORE_FEATURES
        ]
        .fillna(0.5)
        .mean(axis=1)
    )

    validation_rule_prediction = (
        validation_rule_probability >= 0.80
    ).astype(int)

    validation_lr_probability = (
        logistic_regression.predict_proba(
            X_validation
        )[:, 1]
    )

    validation_rf_probability = (
        random_forest.predict_proba(
            X_validation
        )[:, 1]
    )

    test_rule_probability = (
        X_test[
            RULE_SCORE_FEATURES
        ]
        .fillna(0.5)
        .mean(axis=1)
    )

    test_rule_prediction = (
        test_rule_probability >= 0.80
    ).astype(int)

    test_lr_probability = (
        logistic_regression.predict_proba(
            X_test
        )[:, 1]
    )

    test_rf_probability = (
        random_forest.predict_proba(
            X_test
        )[:, 1]
    )

    results = {
        "dataset": {
            "total_cases": len(data),
            "training_cases": len(
                X_train
            ),
            "validation_cases": len(
                X_validation
            ),
            "test_cases": len(
                X_test
            ),
            "positive_cases": int(
                y.sum()
            ),
            "negative_cases": int(
                (1 - y).sum()
            ),
            "data_source": (
                "synthetic prototype"
            ),
            "random_seed": 42,
        },
        "validation_metrics": {
            "rule_based": evaluate(
                y_validation,
                validation_rule_prediction,
                validation_rule_probability,
            ),
            "logistic_regression": evaluate(
                y_validation,
                logistic_regression.predict(
                    X_validation
                ),
                validation_lr_probability,
            ),
            "random_forest": evaluate(
                y_validation,
                random_forest.predict(
                    X_validation
                ),
                validation_rf_probability,
            ),
        },
        "test_metrics": {
            "rule_based": evaluate(
                y_test,
                test_rule_prediction,
                test_rule_probability,
            ),
            "logistic_regression": evaluate(
                y_test,
                logistic_regression.predict(
                    X_test
                ),
                test_lr_probability,
            ),
            "random_forest": evaluate(
                y_test,
                random_forest.predict(
                    X_test
                ),
                test_rf_probability,
            ),
        },
    }

    candidates = {
        "logistic_regression": (
            logistic_regression
        ),
        "random_forest": (
            random_forest
        ),
    }

    selected_name = max(
        candidates,
        key=lambda name: (
            results[
                "validation_metrics"
            ][name]["f1"],
            results[
                "validation_metrics"
            ][name]["roc_auc"],
        ),
    )

    results["selected_model"] = {
        "name": selected_name,
        "selection_rule": (
            "highest validation F1; "
            "ROC-AUC breaks a tie"
        ),
    }

    final_model = clone(
        candidates[selected_name]
    )

    final_X = pd.concat(
        [
            X_train,
            X_validation,
        ]
    )

    final_y = pd.concat(
        [
            y_train,
            y_validation,
        ]
    )

    final_model.fit(
        final_X,
        final_y,
    )

    MODEL_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    RESULTS_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    joblib.dump(
        logistic_regression,
        MODEL_DIR
        / "student4_lr_baseline_v1.joblib",
    )

    joblib.dump(
        random_forest,
        MODEL_DIR
        / "student4_rf_model_v1.joblib",
    )

    joblib.dump(
        final_model,
        MODEL_DIR
        / "student4_evidence_confidence_v1.joblib",
    )

    RESULTS_PATH.write_text(
        json.dumps(
            results,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        json.dumps(
            results,
            indent=2,
        )
    )

    print(
        "IMPORTANT: Report these as "
        "synthetic prototype results only."
    )


if __name__ == "__main__":
    main()