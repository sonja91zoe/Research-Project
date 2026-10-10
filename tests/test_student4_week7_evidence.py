"""Regression tests for missing evidence in the Week 7 integration."""

import json
from pathlib import Path

import pytest

from src.evidence.verification import verify_case


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_valid_mock_case():
    path = (
        PROJECT_ROOT
        / "data"
        / "test_cases"
        / "member3_cases.json"
    )
    cases = json.loads(path.read_text(encoding="utf-8"))

    # Explicit synthetic input, not a real model prediction.
    case = dict(cases[0])
    case["claim_image_consistency"] = 1.0
    return case


@pytest.mark.parametrize("missing_kind", ["absent", "null"])
def test_missing_consistency_does_not_confirm_eligibility(
    missing_kind,
):
    case = load_valid_mock_case()

    baseline = verify_case(case)
    assert baseline.policy_eligible is True

    if missing_kind == "absent":
        case.pop("claim_image_consistency")
    else:
        case["claim_image_consistency"] = None

    result = verify_case(case)

    assert result.policy_eligible is False
    assert "missing" in result.reason.lower()
    assert (
        result.evidence_completeness
        < baseline.evidence_completeness
    )


def test_empty_detected_product_is_unknown_not_mismatch():
    case = load_valid_mock_case()
    case["detected_product"] = ""

    result = verify_case(case)

    assert result.image_order_match == 0.5
    assert result.image_order_match_status == "NOT_AVAILABLE"
    assert result.policy_eligible is True
    assert "not independently identified" in result.reason


def test_unsupported_product_label_is_not_treated_as_mismatch():
    case = load_valid_mock_case()
    case["detected_product"] = "Shoes"

    result = verify_case(case)

    assert result.image_order_match == 0.5
    assert result.image_order_match_status == "NOT_AVAILABLE"
    assert result.policy_eligible is True
