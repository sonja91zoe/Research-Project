import json

from src.image_quality.claim_parser import parse_claim


def test_claim_dataset_v1():
    with open(
        "data/member1/claims_v1.json",
        "r",
        encoding="utf-8"
    ) as file:
        dataset = json.load(file)

    for case in dataset:
        result = parse_claim(case["claim_text"])

        assert result["product"] == case["product"], (
            f'{case["case_id"]}: product mismatch - '
            f'expected {case["product"]}, got {result["product"]}'
        )

        assert result["claimed_defect"] == case["claimed_defect"], (
            f'{case["case_id"]}: defect mismatch - '
            f'expected {case["claimed_defect"]}, '
            f'got {result["claimed_defect"]}'
        )

        assert result["claimed_location"] == case["claimed_location"], (
            f'{case["case_id"]}: location mismatch - '
            f'expected {case["claimed_location"]}, '
            f'got {result["claimed_location"]}'
        )