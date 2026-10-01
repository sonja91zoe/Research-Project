"""Pipeline integration tests with controlled visual evidence.

Image quality, order retrieval, policy verification and decisions
use real project code. Damage results are synthetic test inputs.
These tests do not measure CLIP accuracy.
"""

from pathlib import Path

import pytest
from PIL import Image

from src.agent.pipeline import run_pipeline
from src.common.schemas import CaseInput, Member2Output


class ControlledDetector:
    """Provide explicit synthetic visual evidence for routing tests."""

    def __init__(self, *, consistency=1.0):
        self.consistency = consistency
        self.calls = []

    def detect(self, case_id, image_path, evidence_quality):
        self.calls.append(
            {
                "case_id": case_id,
                "image_path": str(image_path),
                "evidence_quality": evidence_quality,
            }
        )

        if evidence_quality != "good":
            return Member2Output(
                case_id=case_id,
                damage_detected=False,
                damage_type="uncertain",
                damage_confidence=0.0,
                evidence_quality=evidence_quality,
                needs_human_review=True,
                claim_image_consistency=None,
            )

        return Member2Output(
            case_id=case_id,
            detected_product="White T-Shirt",
            damage_detected=True,
            damage_type="hole_or_tear",
            damage_confidence=0.99,
            evidence_quality="good",
            needs_human_review=False,
            claim_image_consistency=self.consistency,
            model_version="synthetic-integration-test",
        )


@pytest.fixture
def image_path(tmp_path):
    """Create a sharp, normally exposed synthetic image."""

    path = tmp_path / "test_image.png"
    image = Image.new("RGB", (128, 128))

    image.putdata(
        [
            (60, 60, 60)
            if (x // 8 + y // 8) % 2
            else (180, 180, 180)
            for y in range(128)
            for x in range(128)
        ]
    )

    image.save(path)
    return path


def make_case(image_path, order_id="ORD003"):
    return CaseInput(
        case_id="PIPELINE_TEST",
        order_id=order_id,
        claim_text="The white t-shirt arrived with a hole.",
        image_paths=[str(image_path)],
    )


@pytest.mark.parametrize(
    ("order_id", "visible", "expected"),
    [
        ("ORD003", True, "AUTO_REFUND"),
        ("ORD003", False, "REQUEST_MORE_EVIDENCE"),
        ("ORD999", True, "HUMAN_REVIEW"),
    ],
)
def test_pipeline_decision_branches(
    image_path,
    order_id,
    visible,
    expected,
):
    detector = ControlledDetector()

    result = run_pipeline(
        make_case(image_path, order_id),
        request_date="2026-08-15",
        relevant_region_visible=visible,
        confidence_method="rule",
        detector=detector,
    )

    assert result["decision"]["decision"] == expected

    for key in ("member1", "member2", "member3", "decision"):
        assert result[key]["case_id"] == "PIPELINE_TEST"

    assert len(detector.calls) == 1
    assert Path(detector.calls[0]["image_path"]) == image_path
    assert detector.calls[0]["evidence_quality"] == (
        "good" if visible else "unusable"
    )

    if expected == "AUTO_REFUND":
        assert result["member3"]["refund_amount"] == 35.0
        assert result["decision"]["refund_risk"] == "LOW"


def test_pipeline_calculates_missing_consistency(image_path):
    result = run_pipeline(
        make_case(image_path),
        request_date="2026-08-15",
        relevant_region_visible=True,
        confidence_method="rule",
        detector=ControlledDetector(consistency=None),
    )

    assert result["member2"]["claim_image_consistency"] == 1.0
    assert "claim_image_consistency" not in result["missing_evidence"]
    assert result["member2_verification"]["verdict"] == "positive"
    assert result["member3"]["policy_eligible"] is True


def test_pipeline_rejects_multiple_images(image_path):
    case = make_case(image_path)
    case.image_paths.append(str(image_path))

    with pytest.raises(ValueError, match="exactly one image"):
        run_pipeline(
            case,
            request_date="2026-08-15",
            relevant_region_visible=True,
            confidence_method="rule",
            detector=ControlledDetector(),
        )
