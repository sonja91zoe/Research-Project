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
from src.damage_detection.damage import DamagePrediction
from src.damage_detection.product import ProductTypeClassifier, ProductTypePrediction
from src.damage_detection.runtime import YOLO_WEIGHTS_ENV
from src.damage_detection.yolo import YoloBackend
import src.damage_detection.runtime as runtime_config


class ControlledDetector:
    """Provide explicit synthetic visual evidence for routing tests."""

    def __init__(
        self, *, consistency=1.0, detected_product="t-shirt", product_confidence=None
    ):
        self.consistency = consistency
        self.detected_product = detected_product
        self.product_confidence = product_confidence
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
            detected_product=self.detected_product,
            product_confidence=self.product_confidence,
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


def test_direct_pipeline_uses_canonical_models_by_default(image_path, monkeypatch):
    monkeypatch.delenv(YOLO_WEIGHTS_ENV, raising=False)
    monkeypatch.setattr(runtime_config, 'find_spec', lambda name: object())
    calls = []

    def predict_damage(self, path):
        calls.append('yolo')
        return DamagePrediction('hole_or_tear', 0.99, 'controlled YOLO')

    def predict_product(self, path):
        calls.append('product')
        return ProductTypePrediction('t-shirt', 0.90, 0.2, 'controlled CLIP product')

    monkeypatch.setattr(YoloBackend, 'predict', predict_damage)
    monkeypatch.setattr(ProductTypeClassifier, 'predict', predict_product)

    result = run_pipeline(
        make_case(image_path), request_date='2026-08-15',
        relevant_region_visible=True, confidence_method='rule',
    )

    assert calls == ['yolo', 'product']
    assert result['member2']['damage_type'] == 'hole_or_tear'
    assert result['member2']['detected_product'] == 't-shirt'
    assert result['member2']['runtime_metadata']['damage_backend'] == 'yolo'
    assert result['member2']['runtime_metadata']['product_classifier_backend'] == 'clip'
    assert result['member2']['runtime_metadata']['damage_inference_completed'] is True
    assert result['member2']['runtime_metadata']['product_classification_completed'] is True
    assert result['member3']['image_order_match_status'] == 'MATCH'


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

    assert len(detector.calls) == (1 if visible else 0)
    if visible:
        assert Path(detector.calls[0]["image_path"]) == image_path
        assert detector.calls[0]["evidence_quality"] == "good"
    else:
        assert result["member2"]["runtime_metadata"]["damage_inference_completed"] is False

    if expected == "AUTO_REFUND":
        assert result["member3"]["refund_amount"] == 35.0
        assert result["decision"]["refund_risk"] == "LOW"


@pytest.mark.parametrize(
    ("detected_product", "product_confidence", "match_status", "eligible", "decision"),
    [
        ("t-shirt", None, "MATCH", True, "AUTO_REFUND"),
        ("skirt", 0.709, "MISMATCH", False, "HUMAN_REVIEW"),
        (None, None, "NOT_AVAILABLE", True, "REQUEST_MORE_EVIDENCE"),
        ("shoes", 0.90, "NOT_AVAILABLE", True, "REQUEST_MORE_EVIDENCE"),
        ("t-shirt", 0.10, "NOT_AVAILABLE", True, "REQUEST_MORE_EVIDENCE"),
    ],
)
def test_product_evidence_controls_end_to_end_decision(
    image_path, detected_product, product_confidence, match_status, eligible, decision
):
    result = run_pipeline(
        make_case(image_path),
        request_date="2026-08-15",
        relevant_region_visible=True,
        confidence_method="rule",
        detector=ControlledDetector(
            detected_product=detected_product,
            product_confidence=product_confidence,
        ),
    )

    assert result["member3"]["image_order_match_status"] == match_status
    assert result["member3"]["policy_eligible"] is eligible
    assert result["decision"]["refund_risk"] == "LOW"
    assert result["decision"]["decision"] == decision


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
