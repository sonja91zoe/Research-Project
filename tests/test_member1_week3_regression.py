from src.image_quality.quality import assess_blur


DARK_HOODIE = "data/member1/images/member1_hoodie_001_dark.jpg"
OCCLUDED_JACKET = "data/member1/images/member1_jacket_001_occluded.jpg"
SLIGHT_BLUR = "data/member1/images/member1_tshirt_001_slight_blur.jpg"
SEVERE_BLUR = "data/member1/images/member1_tshirt_001_severe_blur.jpg"


def test_dark_image_remains_clear_after_stabilisation():
    result = assess_blur(DARK_HOODIE)

    assert result["blur_label"] == "clear"


def test_occluded_image_remains_clear_after_stabilisation():
    result = assess_blur(OCCLUDED_JACKET)

    assert result["blur_label"] == "clear"


def test_true_blur_cases_remain_detectable():
    slight_result = assess_blur(SLIGHT_BLUR)
    severe_result = assess_blur(SEVERE_BLUR)

    assert slight_result["blur_label"] == "slightly_blurred"
    assert severe_result["blur_label"] == "severely_blurred"