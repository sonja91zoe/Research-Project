"""Independent garment-type classification for uploaded evidence images."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class ProductTypePrediction:
    product_type: str | None
    confidence: float
    margin: float
    rationale: str


class ProductTypeClassifier:
    """Zero-shot garment classifier that never reads order metadata or labels."""

    MODEL_NAME = "openai/clip-vit-base-patch32"
    DEFAULT_MIN_CONFIDENCE = 0.24
    DEFAULT_MIN_MARGIN = 0.03
    LABEL_PROMPTS = {
        "jacket": (
            "a photo of a jacket",
            "a garment jacket with sleeves and a front opening",
        ),
        "hoodie": (
            "a photo of a hoodie",
            "a hooded sweatshirt",
        ),
        "t-shirt": (
            "a photo of a t-shirt",
            "a short sleeve tee shirt",
        ),
        "shirt": (
            "a photo of a shirt",
            "a collared or button-up shirt",
        ),
        "trousers": (
            "a photo of trousers",
            "a pair of pants",
        ),
        "dress": (
            "a photo of a dress",
            "a one-piece dress garment",
        ),
        "skirt": (
            "a photo of a skirt",
            "a skirt garment",
        ),
        "sweater": (
            "a photo of a sweater",
            "a knitted jumper or pullover",
        ),
    }

    def __init__(
        self,
        *,
        min_confidence: float = DEFAULT_MIN_CONFIDENCE,
        min_margin: float = DEFAULT_MIN_MARGIN,
        classifier: Callable[..., list[dict[str, Any]]] | None = None,
    ):
        if not 0.0 <= min_confidence <= 1.0:
            raise ValueError("min_confidence must be between 0 and 1")
        if not 0.0 <= min_margin <= 1.0:
            raise ValueError("min_margin must be between 0 and 1")
        self.min_confidence = min_confidence
        self.min_margin = min_margin
        self._classifier = classifier
        self.model_provenance: dict[str, str] | None = None

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

    def score(self, image_path: str | Path) -> dict[str, float]:
        prompts = [
            prompt
            for label_prompts in self.LABEL_PROMPTS.values()
            for prompt in label_prompts
        ]
        results = self._get_classifier()(
            str(Path(image_path)),
            candidate_labels=prompts,
        )
        scores_by_prompt = {
            str(result["label"]): float(result["score"])
            for result in results
        }
        if any(prompt not in scores_by_prompt for prompt in prompts):
            raise RuntimeError("Product classifier returned incomplete scores")
        class_scores = {
            label: sum(scores_by_prompt[prompt] for prompt in label_prompts)
            / len(label_prompts)
            for label, label_prompts in self.LABEL_PROMPTS.items()
        }
        total = sum(class_scores.values())
        if total <= 0.0:
            raise RuntimeError("Product classifier returned no usable score")
        return {label: score / total for label, score in class_scores.items()}

    def predict(self, image_path: str | Path) -> ProductTypePrediction:
        scores = self.score(image_path)
        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        (product_type, confidence), (_, second_score) = ranked[:2]
        margin = confidence - second_score
        if confidence < self.min_confidence or margin < self.min_margin:
            return ProductTypePrediction(
                product_type=None,
                confidence=confidence,
                margin=margin,
                rationale=(
                    "Garment type is uncertain "
                    f"(confidence={confidence:.3f}, margin={margin:.3f})."
                ),
            )
        return ProductTypePrediction(
            product_type=product_type,
            confidence=confidence,
            margin=margin,
            rationale=(
                f"CLIP classified the garment as {product_type} "
                f"(margin={margin:.3f})."
            ),
        )
