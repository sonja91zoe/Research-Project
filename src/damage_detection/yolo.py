"""Local YOLO object-detection backend for Member 2 damage labels."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from src.damage_detection.damage import DamagePrediction


class YoloBackend:
    """Convert a trained two-class YOLO model result to DamagePrediction."""

    LABELS = {0: "hole_or_tear", 1: "stain_or_spot"}

    def __init__(
        self,
        weights: str | Path,
        *,
        confidence_threshold: float = 0.01,
        predictor: Callable[..., Any] | None = None,
    ):
        if not 0.0 <= confidence_threshold <= 1.0:
            raise ValueError("confidence_threshold must be between 0 and 1")
        self.weights = str(weights)
        self.confidence_threshold = confidence_threshold
        self._predictor = predictor

    def _get_predictor(self):
        if self._predictor is None:
            try:
                from ultralytics import YOLO
            except ImportError as exc:
                raise RuntimeError(
                    "YOLO dependencies are missing; install requirements-yolo.txt"
                ) from exc
            self._predictor = YOLO(self.weights)
        return self._predictor

    def predict(self, image_path: Path) -> DamagePrediction:
        results = self._get_predictor()(
            str(image_path), conf=self.confidence_threshold, verbose=False
        )
        if not results or results[0].boxes is None or len(results[0].boxes) == 0:
            return DamagePrediction(
                "uncertain",
                0.0,
                "YOLO found no visible defect; clean controls are not yet available to confirm no_damage.",
            )

        boxes = results[0].boxes
        confidences = boxes.conf.tolist()
        classes = [int(value) for value in boxes.cls.tolist()]
        best_index = max(range(len(confidences)), key=confidences.__getitem__)
        class_id = classes[best_index]
        if class_id not in self.LABELS:
            return DamagePrediction(
                "uncertain",
                float(confidences[best_index]),
                f"YOLO returned unsupported class id {class_id}.",
            )
        label = self.LABELS[class_id]
        return DamagePrediction(
            label,
            float(confidences[best_index]),
            f"YOLO detected {label}; {len(confidences)} candidate box(es).",
        )
