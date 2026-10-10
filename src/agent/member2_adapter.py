"""Connect the real Member 2 damage detector to the Agent."""

from pathlib import Path

from src.common.schemas import (
    CaseInput,
    Member1Output,
    Member2Output,
)
from src.damage_detection.damage import DamageDetector, skipped_damage_output
from src.damage_detection.product import ProductTypeClassifier
from src.damage_detection.runtime import (
    DamageBackend,
    build_member2_runtime,
    member2_runtime_metadata,
)
from src.damage_detection.verification import (
    VerificationResult,
    verify_claim,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def run_member2(
    case: CaseInput,
    member1: Member1Output,
    *,
    detector: DamageDetector | None = None,
    product_classifier: ProductTypeClassifier | None = None,
    yolo_weights: str | Path | None = None,
    backend: DamageBackend = "yolo",
) -> Member2Output:
    """Return Agent-compatible visual evidence with claim verification."""

    return run_member2_verification(
        case,
        member1,
        detector=detector,
        product_classifier=product_classifier,
        yolo_weights=yolo_weights,
        backend=backend,
    ).member2


def run_member2_verification(
    case: CaseInput,
    member1: Member1Output,
    *,
    detector: DamageDetector | None = None,
    product_classifier: ProductTypeClassifier | None = None,
    yolo_weights: str | Path | None = None,
    backend: DamageBackend = "yolo",
) -> VerificationResult:
    """Run real damage detection, then compare it with Member 1's claim."""

    if case.case_id != member1.case_id:
        raise ValueError(
            "CaseInput and Member 1 have different case_id values."
        )

    if len(case.image_paths) != 1:
        raise ValueError(
            "Member 2 adapter V1 requires exactly one image."
        )

    image_path = Path(case.image_paths[0]).expanduser()

    if not image_path.is_absolute():
        image_path = PROJECT_ROOT / image_path

    evidence_quality = (
        "good"
        if (
            member1.image_usable
            and member1.relevant_region_visible
        )
        else "unusable"
    )

    if detector is None:
        runtime = build_member2_runtime(backend=backend, weights=yolo_weights)
        detector = runtime.detector
        if product_classifier is None:
            product_classifier = runtime.product_classifier

    if evidence_quality == "good":
        visual = detector.detect(
            case_id=case.case_id,
            image_path=image_path,
            evidence_quality=evidence_quality,
        )
    else:
        visual = skipped_damage_output(case.case_id, evidence_quality)

    product_classification_completed = False
    if product_classifier is not None and evidence_quality == "good":
        product = product_classifier.predict(image_path)
        product_classification_completed = True
        visual = Member2Output.model_validate(
            {
                **visual.model_dump(),
                "detected_product": product.product_type,
                "product_confidence": product.confidence,
                "rationale": f"{visual.rationale} {product.rationale}",
            }
        )

    visual = Member2Output.model_validate({
        **visual.model_dump(),
        "runtime_metadata": member2_runtime_metadata(
            detector,
            product_classifier,
            damage_inference_completed=evidence_quality == "good",
            product_classification_completed=product_classification_completed,
        ),
    })
    return verify_claim(case, member1, visual)
