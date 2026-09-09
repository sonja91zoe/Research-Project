"""Customer claim parsing module."""


def parse_claim(claim_text: str) -> dict:
    """
    Extract basic refund claim information from customer text.

    Returns:
        {
            "product": str | None,
            "claimed_defect": str | None,
            "claimed_location": str | None
        }
    """

    text = claim_text.lower()

    product = None
    claimed_defect = None
    claimed_location = None

    # -------------------------
    # 1. Product extraction
    # -------------------------
    product_keywords = {
        "jacket": "jacket",
        "hoodie": "hoodie",
        "t-shirt": "t-shirt",
        "tshirt": "t-shirt",
        "shirt": "shirt",
        "pants": "pants",
        "trousers": "pants",
    }

    for keyword, standard_name in product_keywords.items():
        if keyword in text:
            product = standard_name
            break

    # -------------------------
    # 2. Defect extraction
    # -------------------------
    if any(word in text for word in ["tear", "torn", "hole", "ripped", "rip"]):
        claimed_defect = "tear_hole"

    elif any(word in text for word in ["stain", "stained", "mark", "dirty"]):
        claimed_defect = "stain"

    elif any(
        phrase in text
        for phrase in [
            "no visible damage",
            "no damage",
            "not damaged",
        ]
    ):
        claimed_defect = "no_visible_damage"

    # -------------------------
    # 3. Location extraction
    # -------------------------
    location_keywords = {
        "left sleeve": "left_sleeve",
        "right sleeve": "right_sleeve",
        "collar": "collar",
        "front": "front",
        "back": "back",
        "pocket": "pocket",
        "zipper": "zipper",
    }

    for keyword, standard_name in location_keywords.items():
        if keyword in text:
            claimed_location = standard_name
            break

    return {
        "product": product,
        "claimed_defect": claimed_defect,
        "claimed_location": claimed_location,
    }