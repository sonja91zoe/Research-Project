"""Create a small synthetic pilot set for Week 8 experiments.

Labels are explicit scenario expectations, not Agent predictions.
This set does not establish real-world refund accuracy.
"""

import json
from collections import Counter
from copy import deepcopy
from pathlib import Path

from src.common.schemas import (
    Member1Output,
    Member2Output,
    Member3Output,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "data" / "member4" / "week8"


def make_input(case_id, score=0.95, amount=35.0):
    """Create controlled structured evidence, not real image results."""

    return {
        "case_id": case_id,
        "member1": {
            "case_id": case_id,
            "product": "t-shirt",
            "claimed_defect": "tear_hole",
            "claimed_location": "front",
            "image_quality": score,
            "blur_score": 200.0,
            "lighting_score": 1.0,
            "relevant_region_visible": True,
            "image_usable": True,
        },
        "member2": {
            "case_id": case_id,
            "detected_product": "t-shirt",
            "damage_detected": True,
            "damage_type": "hole_or_tear",
            "damage_location": "front",
            "damage_confidence": score,
            "claim_image_consistency": score,
            "evidence_quality": "good",
            "needs_human_review": False,
            "model_version": "synthetic-week8-pilot",
        },
        "member3": {
            "case_id": case_id,
            "order_valid": True,
            "image_order_consistency": score,
            "policy_eligible": True,
            "policy_match_score": score,
            "evidence_completeness": score,
            "refund_amount": amount,
            "policy_source": "Synthetic pilot policy",
        },
    }


def build_cases():
    records = []

    def add(
        split,
        case_id,
        expected,
        reason,
        *,
        score=0.95,
        amount=35.0,
        updates=None,
    ):
        inputs = make_input(case_id, score, amount)

        for member, values in (updates or {}).items():
            inputs[member].update(deepcopy(values))

        # Check that each case follows the shared schema.
        Member1Output(**inputs["member1"])
        Member2Output(**inputs["member2"])
        Member3Output(**inputs["member3"])

        records.append(
            {
                "split": split,
                "inputs": inputs,
                "label": {
                    "case_id": case_id,
                    "expected_decision": expected,
                    "label_reason": reason,
                    "label_source": "manual_scenario_specification",
                },
            }
        )

    add(
        "validation", "W8_V01", "AUTO_REFUND",
        "Strong consistent evidence and a low refund amount.",
    )
    add(
        "validation", "W8_V02", "AUTO_REFUND",
        "Strong evidence at the inclusive low-risk amount boundary.",
        score=0.90, amount=50.0,
    )
    add(
        "validation", "W8_V03", "REQUEST_MORE_EVIDENCE",
        "The uploaded image is unusable.",
        updates={
            "member1": {
                "image_quality": 0.0,
                "image_usable": False,
            },
            "member3": {"policy_eligible": False},
        },
    )
    add(
        "validation", "W8_V04", "REQUEST_MORE_EVIDENCE",
        "The relevant region is not visible.",
        updates={
            "member1": {
                "relevant_region_visible": False,
                "image_usable": False,
            },
            "member3": {"policy_eligible": False},
        },
    )
    add(
        "validation", "W8_V05", "HUMAN_REVIEW",
        "The order cannot be validated.",
        updates={
            "member3": {
                "order_valid": False,
                "policy_eligible": False,
                "refund_amount": 0.0,
            }
        },
    )
    add(
        "validation", "W8_V06", "HUMAN_REVIEW",
        "A high refund amount requires review despite strong evidence.",
        amount=250.0,
    )

    add(
        "validation", "W8_V07", "REQUEST_MORE_EVIDENCE",
        "Evidence score 0.70 is below the initial 0.80 rubric.",
        score=0.70, amount=35.0,
    )
    add(
        "validation", "W8_V08", "REQUEST_MORE_EVIDENCE",
        "Evidence score 0.79 is just below the initial 0.80 rubric.",
        score=0.79, amount=35.0,
    )
    add(
        "validation", "W8_V09", "AUTO_REFUND",
        "Evidence score 0.80 meets the inclusive initial threshold.",
        score=0.80, amount=35.0,
    )
    add(
        "validation", "W8_V10", "AUTO_REFUND",
        "Evidence score 0.85 exceeds the initial 0.80 rubric.",
        score=0.85, amount=35.0,
    )


    add(
        "test", "W8_T01", "AUTO_REFUND",
        "Strong consistent evidence and a low refund amount.",
        score=0.88, amount=42.0,
    )
    add(
        "test", "W8_T02", "AUTO_REFUND",
        "Sufficient evidence under the initial 0.80 confidence rubric.",
        score=0.82, amount=20.0,
    )
    add(
        "test", "W8_T03", "REQUEST_MORE_EVIDENCE",
        "Moderate evidence is insufficient for an automatic refund.",
        score=0.65, amount=35.0,
    )
    add(
        "test", "W8_T04", "REQUEST_MORE_EVIDENCE",
        "The damage module reports poor-quality evidence.",
        updates={
            "member2": {
                "evidence_quality": "poor",
                "needs_human_review": True,
            }
        },
    )
    add(
        "test", "W8_T05", "HUMAN_REVIEW",
        "Refund-policy eligibility is not confirmed.",
        updates={"member3": {"policy_eligible": False}},
    )
    add(
        "test", "W8_T06", "HUMAN_REVIEW",
        "The damage module explicitly requests human review.",
        updates={"member2": {"needs_human_review": True}},
    )

    return records


def main():
    records = build_cases()
    ids = [record["inputs"]["case_id"] for record in records]
    assert len(ids) == len(set(ids)), "Duplicate case IDs"

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for split in ("validation", "test"):
        selected = [
            record for record in records
            if record["split"] == split
        ]

        for kind, key in (
            ("inputs", "inputs"),
            ("labels", "label"),
        ):
            path = OUTPUT_DIR / f"{split}_{kind}.json"
            path.write_text(
                json.dumps(
                    [record[key] for record in selected],
                    indent=2,
                    ensure_ascii=False,
                ) + "\n",
                encoding="utf-8",
            )

        counts = Counter(
            record["label"]["expected_decision"]
            for record in selected
        )
        print(f"{split}: {len(selected)} cases")
        print(dict(counts))

    print(f"\nCreated {len(records)} synthetic pilot cases.")
    print("No model training or evaluation was performed.")
    print(f"Output directory: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()