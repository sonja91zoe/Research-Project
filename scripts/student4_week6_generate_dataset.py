"""Generate reproducible prototype data for Student 4 Week 6.

The generated labels are synthetic. They demonstrate the ML workflow and must
not be presented as real-world model performance.
"""

from pathlib import Path

import numpy as np
import pandas as pd


OUTPUT_PATH = Path(
    "data/member4/evidence_confidence_training_v1.csv"
)

RANDOM_SEED = 42
NUMBER_OF_CASES = 400


def main():
    rng = np.random.default_rng(RANDOM_SEED)

    data = pd.DataFrame(
        {
            "image_quality": rng.beta(
                4, 2, NUMBER_OF_CASES
            ),
            "damage_confidence": rng.beta(
                4, 2, NUMBER_OF_CASES
            ),
            "claim_image_consistency": rng.beta(
                4, 2, NUMBER_OF_CASES
            ),
            "image_order_consistency": rng.beta(
                5, 2, NUMBER_OF_CASES
            ),
            "policy_match_score": rng.beta(
                5, 2, NUMBER_OF_CASES
            ),
            "evidence_completeness": rng.beta(
                5, 2, NUMBER_OF_CASES
            ),
            "image_usable": rng.binomial(
                1, 0.88, NUMBER_OF_CASES
            ),
            "relevant_region_visible": rng.binomial(
                1, 0.86, NUMBER_OF_CASES
            ),
            "damage_detected": rng.binomial(
                1, 0.82, NUMBER_OF_CASES
            ),
            "damage_evidence_quality": rng.choice(
                [1.0, 0.5, 0.0],
                size=NUMBER_OF_CASES,
                p=[0.78, 0.17, 0.05],
            ),
            "damage_needs_human_review": rng.binomial(
                1, 0.12, NUMBER_OF_CASES
            ),
            "order_valid": rng.binomial(
                1, 0.91, NUMBER_OF_CASES
            ),
            "policy_eligible": rng.binomial(
                1, 0.82, NUMBER_OF_CASES
            ),
        }
    )

    score_columns = [
        "image_quality",
        "damage_confidence",
        "claim_image_consistency",
        "image_order_consistency",
        "policy_match_score",
        "evidence_completeness",
    ]

    weighted_score = (
        0.15 * data["image_quality"]
        + 0.20 * data["damage_confidence"]
        + 0.20 * data["claim_image_consistency"]
        + 0.15 * data["image_order_consistency"]
        + 0.12 * data["policy_match_score"]
        + 0.10 * data["evidence_completeness"]
        + 0.08 * data["damage_evidence_quality"]
    )

    lowest_score = data[score_columns].min(axis=1)

    nonlinear_penalty = (
        (lowest_score < 0.35).astype(float) * 0.15
    )

    noisy_score = (
        weighted_score
        - nonlinear_penalty
        + rng.normal(0, 0.07, NUMBER_OF_CASES)
    )

    required_evidence_present = (
        data["image_usable"].astype(bool)
        & data["relevant_region_visible"].astype(bool)
        & data["damage_detected"].astype(bool)
        & (data["damage_evidence_quality"] > 0.0)
        & ~data["damage_needs_human_review"].astype(bool)
        & data["order_valid"].astype(bool)
        & data["policy_eligible"].astype(bool)
    )

    data["evidence_reliable"] = (
        (noisy_score >= 0.68)
        & required_evidence_present
    ).astype(int)

    data.insert(
        0,
        "case_id",
        [
            f"M4_W6_{number:03d}"
            for number in range(
                1,
                NUMBER_OF_CASES + 1,
            )
        ],
    )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    data.to_csv(
        OUTPUT_PATH,
        index=False,
    )

    counts = (
        data["evidence_reliable"]
        .value_counts()
        .sort_index()
    )

    print(
        f"Saved {len(data)} cases to {OUTPUT_PATH}"
    )
    print(counts)
    print(
        "IMPORTANT: This dataset is "
        "synthetic prototype data."
    )


if __name__ == "__main__":
    main()