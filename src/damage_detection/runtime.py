"""Shared Member 2 model selection and inference provenance."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from functools import lru_cache
from importlib.util import find_spec
from pathlib import Path
from typing import Literal

from src.damage_detection.damage import (
    ClipBackend,
    DEFAULT_REVIEW_THRESHOLD,
    DamageDetector,
)
from src.damage_detection.product import ProductTypeClassifier
from src.damage_detection.yolo import YoloBackend


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_YOLO_WEIGHTS = Path("models/member2/best.pt")
YOLO_WEIGHTS_ENV = "MEMBER2_YOLO_WEIGHTS"
DamageBackend = Literal["yolo", "clip"]


@dataclass(frozen=True)
class Member2Runtime:
    detector: DamageDetector
    product_classifier: ProductTypeClassifier


def has_configured_yolo_weights() -> bool:
    """Return whether the YOLO weight environment variable is present."""

    return YOLO_WEIGHTS_ENV in os.environ


def has_available_yolo_weights() -> bool:
    """Return whether configured or bundled YOLO weights are available."""

    try:
        resolve_yolo_weights()
    except FileNotFoundError:
        return False
    return True


def resolve_yolo_weights(weights: str | Path | None = None) -> Path:
    """Resolve an existing YOLO weight or explain how to obtain one."""

    if weights is not None:
        selected = weights
    elif YOLO_WEIGHTS_ENV in os.environ:
        selected = os.environ[YOLO_WEIGHTS_ENV]
        if not selected.strip():
            raise ValueError(f"{YOLO_WEIGHTS_ENV} is set but empty")
    else:
        selected = DEFAULT_YOLO_WEIGHTS
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

    resolved_weights = resolve_yolo_weights(weights)
    if find_spec("ultralytics") is None:
        raise RuntimeError(
            "YOLO dependencies are missing; install requirements-yolo.txt"
        )
    detector = DamageDetector(
        YoloBackend(
            resolved_weights,
            confidence_threshold=confidence_threshold,
        ),
        review_threshold=review_threshold,
    )
    stat = resolved_weights.stat()
    detector.model_provenance = {
        "backend": "yolo",
        "model": "ultralytics.YOLO",
        "weights_path": str(resolved_weights),
        "weights_sha256": _weights_sha256(
            str(resolved_weights), stat.st_size, stat.st_mtime_ns
        ),
    }
    return detector


@lru_cache(maxsize=16)
def _weights_sha256(path: str, size: int, modified_ns: int) -> str:
    """Hash one weight version once, even when direct calls rebuild the runtime."""

    digest = hashlib.sha256()
    with Path(path).open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_member2_runtime(
    *,
    backend: DamageBackend = "yolo",
    weights: str | Path | None = None,
    clip_backend: ClipBackend | None = None,
) -> Member2Runtime:
    """Build the shared damage detector and independent product classifier."""

    if backend == "yolo":
        detector = build_yolo_detector(weights)
    elif backend == "clip":
        if weights is not None:
            raise ValueError("YOLO weights cannot be used with the CLIP damage baseline")
    else:
        raise ValueError("backend must be 'yolo' or 'clip'")

    shared_clip = clip_backend if clip_backend is not None else ClipBackend()
    if backend == "clip":
        detector = DamageDetector(backend=shared_clip)
        detector.model_provenance = {
            "backend": "clip",
            "model": shared_clip.MODEL_NAME,
            "weights_path": None,
            "weights_sha256": None,
        }

    def classify(*args, **kwargs):
        return shared_clip._get_classifier()(*args, **kwargs)

    product_classifier = ProductTypeClassifier(classifier=classify)
    product_classifier.model_provenance = {
        "backend": "clip",
        "model": ProductTypeClassifier.MODEL_NAME,
    }

    return Member2Runtime(
        detector=detector,
        product_classifier=product_classifier,
    )


def member2_runtime_metadata(
    detector: object,
    product_classifier: object | None,
    *,
    damage_inference_completed: bool,
    product_classification_completed: bool,
) -> dict[str, str | bool | None]:
    """Describe only model identities established by the shared factory."""

    damage = getattr(detector, "model_provenance", None) or {}
    product = getattr(product_classifier, "model_provenance", None) or {}
    return {
        "damage_backend": damage.get("backend"),
        "damage_model": damage.get("model"),
        "damage_weights_path": damage.get("weights_path"),
        "damage_weights_sha256": damage.get("weights_sha256"),
        "product_classifier_backend": product.get("backend"),
        "product_model": product.get("model"),
        "damage_inference_completed": damage_inference_completed,
        "product_classification_completed": product_classification_completed,
    }
