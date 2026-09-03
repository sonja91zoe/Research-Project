from src.image_quality.quality import (
    assess_blur,
    assess_lighting,
    assess_image_usability,
    assess_image_quality,
    preprocess_image,
)


CLEAR_IMAGE = "data/member1/images/member1_tshirt_001.jpg"
SLIGHT_BLUR_IMAGE = "data/member1/images/member1_tshirt_001_slight_blur.jpg"
SEVERE_BLUR_IMAGE = "data/member1/images/member1_tshirt_001_severe_blur.jpg"
DARK_IMAGE = "data/member1/images/member1_hoodie_001_dark.jpg"
OVEREXPOSED_IMAGE = (
    "data/member1/images/member1_jacket_001_overexposed.jpg"
)


def test_blur_assessment():
    assert assess_blur(CLEAR_IMAGE)["blur_label"] == "clear"
    assert (
        assess_blur(SLIGHT_BLUR_IMAGE)["blur_label"]
        == "slightly_blurred"
    )
    assert (
        assess_blur(SEVERE_BLUR_IMAGE)["blur_label"]
        == "severely_blurred"
    )


def test_lighting_assessment():
    assert assess_lighting(CLEAR_IMAGE)["lighting_label"] == "normal"
    assert assess_lighting(DARK_IMAGE)["lighting_label"] == "dark"
    assert (
        assess_lighting(OVEREXPOSED_IMAGE)["lighting_label"]
        == "overexposed"
    )


def test_image_usability():
    assert assess_image_usability(CLEAR_IMAGE)["image_usable"] is True

    assert (
        assess_image_usability(SEVERE_BLUR_IMAGE)["image_usable"]
        is False
    )

    assert assess_image_usability(DARK_IMAGE)["image_usable"] is False

    assert (
        assess_image_usability(OVEREXPOSED_IMAGE)["image_usable"]
        is False
    )


def test_relevant_region_visibility():
    result = assess_image_usability(
        CLEAR_IMAGE,
        relevant_region_visible=False,
    )

    assert result["image_usable"] is False
    assert result["reason"] == "relevant_region_not_visible"


def test_preprocessing():
    image, gray = preprocess_image(CLEAR_IMAGE)

    assert image.shape[:2] == gray.shape
    assert max(image.shape[:2]) <= 1024


def test_complete_image_quality_output():
    result = assess_image_quality(CLEAR_IMAGE)

    expected_keys = {
        "blur_score",
        "blur_label",
        "brightness_score",
        "highlight_ratio",
        "lighting_label",
        "relevant_region_visible",
        "image_usable",
        "usability_reason",
    }

    assert expected_keys.issubset(result.keys())
    assert result["image_usable"] is True