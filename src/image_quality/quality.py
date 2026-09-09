"""Image quality assessment module."""

from pathlib import Path

import cv2


def calculate_blur_score(image_path: str) -> float:
    """
    Calculate image sharpness using histogram equalization
    followed by the variance of the Laplacian.

    A higher score generally indicates a sharper image.
    A lower score generally indicates a blurrier image.
    """
    path = Path(image_path)

    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    image = cv2.imread(str(path))

    if image is None:
        raise ValueError(f"Unable to read image: {image_path}")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Week 3 stabilisation:
    # Reduce the influence of lighting conditions before blur assessment.
    equalized = cv2.equalizeHist(gray)

    blur_score = cv2.Laplacian(
        equalized,
        cv2.CV_64F,
    ).var()

    return float(blur_score)


def assess_blur(image_path: str) -> dict:
    """
    Assess image blur level.

    Returns:
        {
            "blur_score": float,
            "blur_label": str
        }
    """
    blur_score = calculate_blur_score(image_path)

    # Week 3 stabilised thresholds based on the controlled evaluation dataset.
    # These remain provisional and can be refined with additional data.
    if blur_score < 30:
        blur_label = "severely_blurred"
    elif blur_score < 150:
        blur_label = "slightly_blurred"
    else:
        blur_label = "clear"

    return {
        "blur_score": round(blur_score, 2),
        "blur_label": blur_label,
    }


def calculate_brightness_score(image_path: str) -> float:
    """
    Calculate the average grayscale brightness of an image.

    The score ranges approximately from:
    0   = completely dark
    255 = completely bright
    """
    path = Path(image_path)

    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    image = cv2.imread(str(path))

    if image is None:
        raise ValueError(f"Unable to read image: {image_path}")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    brightness_score = gray.mean()

    return float(brightness_score)


def calculate_highlight_ratio(image_path: str) -> float:
    """
    Calculate the proportion of very bright pixels in an image.

    A high ratio may indicate overexposure or highlight clipping.
    """
    path = Path(image_path)

    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    image = cv2.imread(str(path))

    if image is None:
        raise ValueError(f"Unable to read image: {image_path}")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    highlight_pixels = (gray >= 245).sum()
    total_pixels = gray.size

    highlight_ratio = highlight_pixels / total_pixels

    return float(highlight_ratio)


def assess_lighting(image_path: str) -> dict:
    """
    Assess image lighting quality using average brightness
    and highlight clipping ratio.

    Returns:
        {
            "brightness_score": float,
            "highlight_ratio": float,
            "lighting_label": str
        }
    """
    brightness_score = calculate_brightness_score(image_path)
    highlight_ratio = calculate_highlight_ratio(image_path)

    # V1 thresholds calibrated using the controlled Week 1 dataset.
    # These thresholds are provisional and can be refined with more data.
    if highlight_ratio > 0.05:
        lighting_label = "overexposed"
    elif brightness_score < 50:
        lighting_label = "dark"
    else:
        lighting_label = "normal"

    return {
        "brightness_score": round(brightness_score, 2),
        "highlight_ratio": round(highlight_ratio, 4),
        "lighting_label": lighting_label,
    }


def preprocess_image(image_path: str, max_dimension: int = 1024):
    """
    Load and resize an image while preserving its aspect ratio.

    Returns:
        original/resized BGR image and grayscale image.
    """
    path = Path(image_path)

    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    image = cv2.imread(str(path))

    if image is None:
        raise ValueError(f"Unable to read image: {image_path}")

    height, width = image.shape[:2]

    if max(height, width) > max_dimension:
        scale = max_dimension / max(height, width)

        new_width = int(width * scale)
        new_height = int(height * scale)

        image = cv2.resize(
            image,
            (new_width, new_height),
            interpolation=cv2.INTER_AREA,
        )

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    return image, gray


def assess_image_usability(
    image_path: str,
    relevant_region_visible: bool = True,
) -> dict:
    """
    Determine whether an image is usable for refund evidence assessment.

    V1 usability is based on:
    - blur quality
    - lighting quality
    - relevant region visibility

    Returns:
        {
            "image_usable": bool,
            "reason": str
        }
    """
    blur_result = assess_blur(image_path)
    lighting_result = assess_lighting(image_path)

    if not relevant_region_visible:
        return {
            "image_usable": False,
            "reason": "relevant_region_not_visible",
        }

    if blur_result["blur_label"] == "severely_blurred":
        return {
            "image_usable": False,
            "reason": "severely_blurred",
        }

    if lighting_result["lighting_label"] == "dark":
        return {
            "image_usable": False,
            "reason": "insufficient_lighting",
        }

    if lighting_result["lighting_label"] == "overexposed":
        return {
            "image_usable": False,
            "reason": "overexposed",
        }

    return {
        "image_usable": True,
        "reason": "usable",
    }


def assess_image_quality(
    image_path: str,
    relevant_region_visible: bool = True,
) -> dict:
    """
    Run the complete Image Quality Module V1.

    Combines:
    - blur assessment
    - lighting assessment
    - relevant-region visibility
    - overall image usability

    Returns a structured image-quality result.
    """
    blur_result = assess_blur(image_path)
    lighting_result = assess_lighting(image_path)
    usability_result = assess_image_usability(
        image_path,
        relevant_region_visible=relevant_region_visible,
    )

    return {
        "blur_score": blur_result["blur_score"],
        "blur_label": blur_result["blur_label"],
        "brightness_score": lighting_result["brightness_score"],
        "highlight_ratio": lighting_result["highlight_ratio"],
        "lighting_label": lighting_result["lighting_label"],
        "relevant_region_visible": relevant_region_visible,
        "image_usable": usability_result["image_usable"],
        "usability_reason": usability_result["reason"],
    }