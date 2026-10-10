"""Regression coverage for persisted Member 2 YOLO runtime configuration."""

from pathlib import Path
import hashlib

import pytest

import src.damage_detection.runtime as runtime_config
from scripts.member2_realtime_demo import run_demo
from src.agent.member2_adapter import run_member2, run_member2_verification
from src.common.schemas import CaseInput, Member1Output
from src.damage_detection.damage import ClipBackend, DamagePrediction
from src.damage_detection.product import ProductTypeClassifier, ProductTypePrediction
from src.damage_detection.runtime import (
    YOLO_WEIGHTS_ENV,
    build_member2_runtime,
    build_yolo_detector,
    has_available_yolo_weights,
    member2_runtime_metadata,
    resolve_yolo_weights,
)
from src.damage_detection.yolo import YoloBackend


def test_explicit_weight_path_is_resolved(tmp_path: Path):
    weights = tmp_path / "best.pt"
    weights.write_bytes(b"test-weight")

    assert resolve_yolo_weights(weights) == weights


def test_missing_weight_explains_recovery_path(tmp_path: Path, monkeypatch):
    monkeypatch.delenv(YOLO_WEIGHTS_ENV, raising=False)

    with pytest.raises(FileNotFoundError, match="Week 2 YOLO training"):
        resolve_yolo_weights(tmp_path / "missing.pt")


def test_detector_uses_the_resolved_weight_without_loading_ultralytics(tmp_path: Path):
    weights = tmp_path / "best.pt"
    weights.write_bytes(b"test-weight")

    detector = build_yolo_detector(weights, review_threshold=0.75)

    assert detector.review_threshold == 0.75
    assert detector.backend.weights == str(weights)
    assert detector.backend.confidence_threshold == 0.01


def test_bundled_weight_is_available_for_the_demo():
    assert has_available_yolo_weights() is True
    assert resolve_yolo_weights().name == "best.pt"


def test_default_runtime_uses_bundled_yolo_and_clip_product(monkeypatch):
    monkeypatch.delenv(YOLO_WEIGHTS_ENV, raising=False)
    monkeypatch.setattr(runtime_config, "find_spec", lambda name: object())

    configured = build_member2_runtime()

    assert isinstance(configured.detector.backend, YoloBackend)
    assert configured.detector.backend.weights == str(resolve_yolo_weights())
    assert isinstance(configured.product_classifier, ProductTypeClassifier)


def test_invalid_configured_weight_does_not_fall_back(monkeypatch, tmp_path):
    missing = tmp_path / "missing.pt"
    monkeypatch.setenv(YOLO_WEIGHTS_ENV, str(missing))

    with pytest.raises(FileNotFoundError, match="Member 2 YOLO weights were not found"):
        build_member2_runtime()


def test_configured_weight_uses_the_selected_file(monkeypatch, tmp_path):
    selected = tmp_path / "alternate.pt"
    selected.write_bytes(b"test-weight")
    monkeypatch.setenv(YOLO_WEIGHTS_ENV, str(selected))
    monkeypatch.setattr(runtime_config, "find_spec", lambda name: object())

    configured = build_member2_runtime()

    assert configured.detector.backend.weights == str(selected)
    metadata = member2_runtime_metadata(
        configured.detector, configured.product_classifier,
        damage_inference_completed=False,
        product_classification_completed=False,
    )
    assert metadata['damage_backend'] == 'yolo'
    assert metadata['damage_weights_path'] == str(selected)
    assert metadata['damage_weights_sha256'] == hashlib.sha256(b'test-weight').hexdigest()
    assert metadata['product_classifier_backend'] == 'clip'
    assert metadata['product_model'] == ProductTypeClassifier.MODEL_NAME


def test_empty_configured_weight_does_not_use_default(monkeypatch):
    monkeypatch.setenv(YOLO_WEIGHTS_ENV, "")

    with pytest.raises(ValueError, match="MEMBER2_YOLO_WEIGHTS is set but empty"):
        build_member2_runtime()


def test_missing_default_weight_does_not_fall_back(monkeypatch, tmp_path):
    monkeypatch.delenv(YOLO_WEIGHTS_ENV, raising=False)
    monkeypatch.setattr(runtime_config, "DEFAULT_YOLO_WEIGHTS", tmp_path / "missing.pt")

    with pytest.raises(FileNotFoundError, match="Member 2 YOLO weights were not found"):
        build_member2_runtime()


def test_missing_yolo_dependency_is_explicit(monkeypatch):
    monkeypatch.delenv(YOLO_WEIGHTS_ENV, raising=False)
    monkeypatch.setattr(runtime_config, "find_spec", lambda name: None)

    with pytest.raises(RuntimeError, match="requirements-yolo.txt"):
        build_member2_runtime()


def test_clip_damage_baseline_requires_explicit_selection(monkeypatch, tmp_path):
    monkeypatch.setenv(YOLO_WEIGHTS_ENV, str(tmp_path / "missing.pt"))

    def fake_clip(_image, *, candidate_labels):
        return [
            {"label": label, "score": 0.9 if index < 3 else 0.01}
            for index, label in enumerate(candidate_labels)
        ]

    configured = build_member2_runtime(
        backend="clip", clip_backend=ClipBackend(classifier=fake_clip)
    )
    image = tmp_path / "garment.jpg"
    image.write_bytes(b"controlled image")

    assert isinstance(configured.detector.backend, ClipBackend)
    assert isinstance(configured.product_classifier, ProductTypeClassifier)
    assert configured.detector.detect("CLIP-BASELINE", image).damage_type == "hole_or_tear"
    metadata = member2_runtime_metadata(
        configured.detector, configured.product_classifier,
        damage_inference_completed=True,
        product_classification_completed=True,
    )
    assert metadata['damage_backend'] == 'clip'
    assert metadata['damage_model'] == ClipBackend.MODEL_NAME
    assert metadata['damage_weights_path'] is None
    assert metadata['damage_weights_sha256'] is None
    assert metadata['product_classifier_backend'] == 'clip'


def fake_model_predictions(monkeypatch, product="jacket"):
    monkeypatch.delenv(YOLO_WEIGHTS_ENV, raising=False)
    monkeypatch.setattr(runtime_config, "find_spec", lambda name: object())
    calls = []

    def predict_damage(self, image_path):
        calls.append("yolo")
        return DamagePrediction("hole_or_tear", 0.9, "controlled YOLO")

    def predict_product(self, image_path):
        calls.append("product")
        return ProductTypePrediction(product, 0.9, 0.2, "controlled CLIP product")

    monkeypatch.setattr(YoloBackend, "predict", predict_damage)
    monkeypatch.setattr(ProductTypeClassifier, "predict", predict_product)
    return calls


@pytest.mark.parametrize("entrypoint", [run_member2, run_member2_verification])
def test_direct_agent_defaults_to_yolo_and_product_classifier(
    tmp_path, monkeypatch, entrypoint
):
    calls = fake_model_predictions(monkeypatch)
    image = tmp_path / "garment.jpg"
    image.write_bytes(b"controlled image")
    case = CaseInput(
        case_id="DEFAULT-MEMBER2", order_id="ORD001",
        claim_text="The jacket has a hole.", image_paths=[str(image)],
    )
    member1 = Member1Output(
        case_id=case.case_id, product="jacket", claimed_defect="hole",
        image_quality=0.9, blur_score=0.1, lighting_score=0.9,
        relevant_region_visible=True, image_usable=True,
    )

    result = entrypoint(case, member1)
    visual = result.member2 if hasattr(result, "member2") else result

    assert calls == ["yolo", "product"]
    assert visual.damage_type == "hole_or_tear"
    assert visual.detected_product == "jacket"
    assert visual.product_confidence == 0.9
    metadata = visual.runtime_metadata
    assert metadata['damage_backend'] == 'yolo'
    assert metadata['damage_weights_path'] == str(resolve_yolo_weights())
    assert len(metadata['damage_weights_sha256']) == 64
    assert metadata['product_classifier_backend'] == 'clip'
    assert metadata['product_model'] == ProductTypeClassifier.MODEL_NAME
    assert metadata['damage_inference_completed'] is True
    assert metadata['product_classification_completed'] is True


def test_realtime_script_uses_canonical_default(tmp_path, monkeypatch):
    calls = fake_model_predictions(monkeypatch)
    image = tmp_path / "garment.jpg"
    image.write_bytes(b"controlled image")

    result = run_demo(image, "The jacket has a hole.")

    assert calls == ["yolo", "product"]
    assert result["member2"]["detected_product"] == "jacket"
