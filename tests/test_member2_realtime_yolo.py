"""Regression coverage for persisted Member 2 YOLO runtime configuration."""

from pathlib import Path

import pytest

from src.damage_detection.runtime import (
    YOLO_WEIGHTS_ENV,
    build_yolo_detector,
    has_available_yolo_weights,
    resolve_yolo_weights,
)


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
