"""Connect the real Member 2 damage detector to the Agent."""

from pathlib import Path

from src.common.schemas import (
    CaseInput,
    Member1Output,
    Member2Output,
)
from src.damage_detection.damage import (
    ClipBackend,
    DamageDetector,
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
) -> Member2Output:
    """Return Agent-compatible visual evidence with claim verification."""

    return run_member2_verification(
        case,
        member1,
        detector=detector,
    ).member2


def run_member2_verification(
    case: CaseInput,
    member1: Member1Output,
    *,
    detector: DamageDetector | None = None,
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
        detector = DamageDetector(
            backend=ClipBackend(),
        )

    visual = detector.detect(
        case_id=case.case_id,
        image_path=image_path,
        evidence_quality=evidence_quality,
    )

    return verify_claim(case, member1, visual)
