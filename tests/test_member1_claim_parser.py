from src.image_quality.claim_parser import parse_claim


def test_parse_claim():
    claim = "The black jacket arrived with a tear on the left sleeve."

    result = parse_claim(claim)

    assert result["product"] == "jacket"
    assert result["claimed_defect"] == "tear_hole"
    assert result["claimed_location"] == "left_sleeve"