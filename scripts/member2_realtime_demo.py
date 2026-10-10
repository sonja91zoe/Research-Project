"""Run the real Member 2 YOLO detector and claim-image verification.

Example:
  python -m scripts.member2_realtime_demo --image garment.jpg \
    --claim-text "The jacket has a visible tear." \
    --weights models/member2/best.pt
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.agent.member2_adapter import run_member2_verification
from src.common.schemas import CaseInput, Member1Output
from src.damage_detection.runtime import DamageBackend
from src.image_quality.claim_parser import parse_claim


def run_demo(
    image: Path,
    claim_text: str,
    weights: Path | None = None,
    *,
    case_id: str = "MEMBER2-REALTIME-001",
    backend: DamageBackend = "yolo",
) -> dict[str, object]:
    """Return the Agent-compatible output for one real image."""

    case = CaseInput(
        case_id=case_id,
        order_id="MEMBER2-DEMO",
        claim_text=claim_text,
        image_paths=[str(image)],
    )
    member1 = Member1Output(
        case_id=case_id,
        image_quality=1.0,
        blur_score=0.0,
        lighting_score=1.0,
        relevant_region_visible=True,
        image_usable=True,
        **parse_claim(claim_text),
    )
    verification = run_member2_verification(
        case,
        member1,
        yolo_weights=weights,
        backend=backend,
    )
    return verification.model_dump()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--claim-text", required=True)
    parser.add_argument("--weights", type=Path)
    parser.add_argument("--backend", choices=("yolo", "clip"), default="yolo")
    parser.add_argument("--case-id", default="MEMBER2-REALTIME-001")
    args = parser.parse_args()
    print(
        json.dumps(
            run_demo(
                args.image, args.claim_text, args.weights,
                case_id=args.case_id, backend=args.backend,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
