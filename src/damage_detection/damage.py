"""Member 2 image-only damage detection for Week 2."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Literal, Protocol

from src.common.schemas import Member2Output


DamageType = Literal["hole_or_tear", "stain_or_spot", "no_damage", "uncertain"]
EvidenceQuality = Literal["good", "poor", "unusable"]
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

# Provisional prototype gates. These are workflow thresholds, not calibrated
# probabilities. Keep them explicit so validation can replace them later.
MIN_USABLE_DAMAGE_CONFIDENCE = 0.10
DEFAULT_REVIEW_THRESHOLD = 0.15


@dataclass(frozen=True)
class DamagePrediction:
    damage_type: DamageType
    confidence: float
    rationale: str
    detected_product: str | None = None
    product_confidence: float | None = None
    damage_location: str | None = None


class VisionBackend(Protocol):
    """Adapter contract for a pretrained vision or multimodal model."""

    def predict(self, image_path: Path) -> DamagePrediction: ...


class DamageDetector:
    """Validate an image, apply the safety gate, and return Member2Output."""

    def __init__(
        self,
        backend: VisionBackend,
        review_threshold: float = DEFAULT_REVIEW_THRESHOLD,
    ):
        if not 0.0 <= review_threshold <= 1.0:
            raise ValueError("review_threshold must be between 0 and 1")

        self.backend = backend
        self.review_threshold = review_threshold
        self.model_provenance: dict[str, str | None] | None = None

    def detect(
        self,
        case_id: str,
        image_path: str | Path,
        evidence_quality: EvidenceQuality = "good",
    ) -> Member2Output:
        path = Path(image_path)
        self._validate_image(path)

        if evidence_quality != "good":
            return skipped_damage_output(case_id, evidence_quality)

        prediction = self.backend.predict(path)

        # Clamp model confidence into the valid [0, 1] range.
        confidence = min(1.0, max(0.0, float(prediction.confidence)))

        # A raw YOLO prediction such as hole_or_tear or stain_or_spot should
        # not automatically become usable damage evidence.
        #
        # Below MIN_USABLE_DAMAGE_CONFIDENCE, the candidate is retained only
        # through its confidence/rationale for traceability, while the formal
        # Member 2 output is downgraded to "uncertain".
        is_damage_prediction = prediction.damage_type in {
            "hole_or_tear",
            "stain_or_spot",
        }

        below_usable_damage_threshold = (
            is_damage_prediction
            and confidence < MIN_USABLE_DAMAGE_CONFIDENCE
        )

        effective_damage_type: DamageType = (
            "uncertain"
            if below_usable_damage_threshold
            else prediction.damage_type
        )

        effective_damage_location = (
            None
            if below_usable_damage_threshold
            else prediction.damage_location
        )

        if below_usable_damage_threshold:
            rationale = (
                f"{prediction.rationale} "
                f"Raw damage candidate was suppressed because confidence "
                f"{confidence:.3f} is below the minimum usable damage "
                f"threshold {MIN_USABLE_DAMAGE_CONFIDENCE:.2f}."
            )
        else:
            rationale = prediction.rationale

        return Member2Output(
            case_id=case_id,
            detected_product=prediction.detected_product,
            product_confidence=prediction.product_confidence,
            damage_detected=(
                is_damage_prediction
                and not below_usable_damage_threshold
            ),
            damage_type=effective_damage_type,
            damage_location=effective_damage_location,
            damage_confidence=confidence,
            evidence_quality=evidence_quality,
            needs_human_review=(
                effective_damage_type == "uncertain"
                or confidence < self.review_threshold
            ),
            rationale=rationale,
        )

    @staticmethod
    def _validate_image(path: Path) -> None:
        if not path.is_file():
            raise FileNotFoundError(f"Image not found: {path}")

        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Unsupported image type: {path.suffix or '<none>'}"
            )

        if path.stat().st_size == 0:
            raise ValueError("Image file is empty")


def skipped_damage_output(
    case_id: str,
    evidence_quality: EvidenceQuality,
) -> Member2Output:
    """Represent a quality-gated image without calling a damage backend."""

    return Member2Output(
        case_id=case_id,
        damage_detected=False,
        damage_type="uncertain",
        damage_confidence=0.0,
        evidence_quality=evidence_quality,
        needs_human_review=True,
        rationale=(
            "Insufficient image evidence; request another photo or human review."
        ),
    )


class FixedBackend:
    """Deterministic backend used by automated integration tests."""

    def __init__(self, prediction: DamagePrediction):
        self.prediction = prediction

    def predict(self, image_path: Path) -> DamagePrediction:
        return self.prediction


class ClipBackend:
    """Free, local zero-shot classifier using openai/clip-vit-base-patch32."""

    MODEL_NAME = "openai/clip-vit-base-patch32"

    LABEL_PROMPTS = {
        "hole_or_tear": (
            "a close-up photo of a hole in garment fabric",
            "torn clothing with ripped fabric edges",
            "a visible opening caused by missing or torn textile fibers",
        ),
        "stain_or_spot": (
            "a close-up photo of a stain on garment fabric",
            "clothing with a visible spot or localized discoloration",
            "a mark or residue visibly different from the surrounding textile",
        ),
        "no_damage": (
            "clean intact garment fabric without damage",
            "undamaged clothing with no hole, tear, stain, or spot",
            "normal textile texture without a defect",
        ),
    }

    def __init__(
        self,
        *,
        min_confidence: float = 0.45,
        min_margin: float = 0.05,
        classifier: Callable[..., list[dict[str, Any]]] | None = None,
    ):
        self.min_confidence = min_confidence
        self.min_margin = min_margin
        self._classifier = classifier

    def _get_classifier(self):
        if self._classifier is None:
            try:
                from transformers import pipeline
            except ImportError as exc:
                raise RuntimeError(
                    "CLIP dependencies are missing; install requirements.txt"
                ) from exc

            self._classifier = pipeline(
                "zero-shot-image-classification",
                model=self.MODEL_NAME,
            )

        return self._classifier

    def score(self, image_path: Path) -> dict[str, float]:
        classifier = self._get_classifier()

        prompts = [
            prompt
            for group in self.LABEL_PROMPTS.values()
            for prompt in group
        ]

        results = classifier(
            str(image_path),
            candidate_labels=prompts,
        )

        if len(results) < len(prompts):
            raise RuntimeError(
                "CLIP backend returned incomplete candidate scores"
            )

        scores_by_prompt = {
            str(result["label"]): float(result["score"])
            for result in results
        }

        class_scores = {
            label: sum(
                scores_by_prompt[prompt]
                for prompt in label_prompts
            ) / len(label_prompts)
            for label, label_prompts in self.LABEL_PROMPTS.items()
        }

        total = sum(class_scores.values())

        return {
            label: score / total
            for label, score in class_scores.items()
        }

    def predict_many(
        self,
        image_paths: list[Path],
    ) -> DamagePrediction:
        if not image_paths:
            raise ValueError("at least one image view is required")

        view_scores = [
            self.score(path)
            for path in image_paths
        ]

        combined = {
            label: sum(
                scores[label]
                for scores in view_scores
            ) / len(view_scores)
            for label in self.LABEL_PROMPTS
        }

        ranked = sorted(
            combined.items(),
            key=lambda item: item[1],
            reverse=True,
        )

        (predicted_label, confidence), (_, second_score) = ranked[:2]
        margin = confidence - second_score

        if (
            confidence < self.min_confidence
            or margin < self.min_margin
        ):
            return DamagePrediction(
                "uncertain",
                confidence,
                (
                    "CLIP multi-view result is uncertain "
                    f"(top-two margin={margin:.3f})."
                ),
            )

        return DamagePrediction(
            predicted_label,
            confidence,
            (
                f"CLIP combined {len(image_paths)} view(s) "
                f"(top-two margin={margin:.3f})."
            ),
        )

    def predict(
        self,
        image_path: Path,
    ) -> DamagePrediction:
        return self.predict_many([image_path])