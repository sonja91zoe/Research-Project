"""Runtime configuration for the persisted Member 2 YOLO detector."""

from __future__ import annotations

import os
from pathlib import Path

from src.damage_detection.damage import (
    DEFAULT_REVIEW_THRESHOLD,
    DamageDetector,
)
from src.damage_detection.yolo import YoloBackend


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_YOLO_WEIGHTS = Path("models/member2/best.pt")
YOLO_WEIGHTS_ENV = "MEMBER2_YOLO_WEIGHTS"


def has_configured_yolo_weights() -> bool:
    """Return whether the runtime has explicitly selected a YOLO weight."""

    return bool(os.getenv(YOLO_WEIGHTS_ENV, "").strip())


def has_available_yolo_weights() -> bool:
    """Return whether configured or bundled YOLO weights are available."""

    try:
        resolve_yolo_weights()
    except FileNotFoundError:
        return False
    return True


def resolve_yolo_weights(weights: str | Path | None = None) -> Path:
    """Resolve an existing YOLO weight or explain how to obtain one."""

    selected = weights or os.getenv(YOLO_WEIGHTS_ENV) or DEFAULT_YOLO_WEIGHTS
    path = Path(selected).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    if not path.is_file():
        raise FileNotFoundError(
            "Member 2 YOLO weights were not found at "
            f"{path}. Run the 'Week 2 YOLO training' workflow, download the "
            "member2-week2-yolo-model artifact, then set MEMBER2_YOLO_WEIGHTS "
            "or place best.pt at models/member2/best.pt."
        )
    return path


def build_yolo_detector(
    weights: str | Path | None = None,
    *,
    review_threshold: float = DEFAULT_REVIEW_THRESHOLD,
    confidence_threshold: float = 0.01,
) -> DamageDetector:
    """Build the safety-gated detector used by the Member 2 Agent adapter."""

    return DamageDetector(
        YoloBackend(
            resolve_yolo_weights(weights),
            confidence_threshold=confidence_threshold,
        ),
        review_threshold=review_threshold,
    )
