"""Run Member 1, the real Member 2 detector, verification, and the Agent."""

import argparse
import json

from src.agent.pipeline import run_pipeline
from src.common.schemas import CaseInput


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--image",
        default="data/member1/images/member1_jacket_001.jpg",
        help="Path to one garment image.",
    )
    parser.add_argument(
        "--claim",
        default="The jacket arrived with a tear.",
        help="Customer claim text.",
    )
    parser.add_argument("--order-id", default="ORD001")
    parser.add_argument("--request-date", default="2026-08-15")
    parser.add_argument(
        "--region-not-visible",
        action="store_true",
        help="Mark the relevant garment region as not visible.",
    )
    arguments = parser.parse_args()

    case = CaseInput(
        case_id="MEMBER2-WEEK7-INTEGRATION-DEMO",
        order_id=arguments.order_id,
        claim_text=arguments.claim,
        image_paths=[arguments.image],
    )
    result = run_pipeline(
        case,
        request_date=arguments.request_date,
        relevant_region_visible=not arguments.region_not_visible,
        confidence_method="rule",
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
