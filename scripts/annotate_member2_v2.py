"""Simple local YOLO annotator for Member 2 v2."""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2


ROOT = Path("data/member2_v2")

CATEGORY_MAP = {
    "hole_or_tear": 0,
    "stain_or_spot": 1,
}

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def resize_for_screen(image, max_width=1200, max_height=800):
    height, width = image.shape[:2]

    scale = min(
        1.0,
        max_width / width,
        max_height / height,
    )

    if scale == 1.0:
        return image, scale

    resized = cv2.resize(
        image,
        (
            int(width * scale),
            int(height * scale),
        ),
    )

    return resized, scale


def annotate_category(category: str, force: bool = False) -> None:
    if category not in CATEGORY_MAP:
        raise ValueError(f"Unsupported category: {category}")

    class_id = CATEGORY_MAP[category]

    image_dir = ROOT / "raw" / category
    label_dir = ROOT / "raw_labels" / category

    label_dir.mkdir(parents=True, exist_ok=True)

    images = sorted(
        path
        for path in image_dir.iterdir()
        if path.is_file()
        and path.suffix.lower() in IMAGE_EXTENSIONS
    )

    if not images:
        print(f"No images found in: {image_dir}")
        return

    print(f"\nCategory: {category}")
    print(f"Class ID: {class_id}")
    print(f"Images: {len(images)}")
    print()
    print("Controls:")
    print("  Drag mouse = draw bounding box")
    print("  ENTER/SPACE = confirm box")
    print("  C = cancel current selection")
    print()

    for index, image_path in enumerate(images, start=1):
        label_path = label_dir / f"{image_path.stem}.txt"

        if label_path.exists() and not force:
            print(
                f"[{index}/{len(images)}] "
                f"Already labelled: {image_path.name}"
            )
            continue

        image = cv2.imread(str(image_path))

        if image is None:
            print(f"Could not read image: {image_path}")
            continue

        original_height, original_width = image.shape[:2]

        display_image, scale = resize_for_screen(image)

        window_name = (
            f"{category} | "
            f"{index}/{len(images)} | "
            f"{image_path.name}"
        )

        x, y, width, height = cv2.selectROI(
            window_name,
            display_image,
            showCrosshair=True,
            fromCenter=False,
        )

        cv2.destroyWindow(window_name)

        if width <= 0 or height <= 0:
            print(
                f"[{index}/{len(images)}] "
                f"Skipped: {image_path.name}"
            )
            continue

        # Convert display coordinates back to original image coordinates.
        x = x / scale
        y = y / scale
        width = width / scale
        height = height / scale

        # Convert to YOLO normalized format:
        # class x_center y_center width height
        x_center = (x + width / 2) / original_width
        y_center = (y + height / 2) / original_height
        norm_width = width / original_width
        norm_height = height / original_height

        label_text = (
            f"{class_id} "
            f"{x_center:.6f} "
            f"{y_center:.6f} "
            f"{norm_width:.6f} "
            f"{norm_height:.6f}\n"
        )

        label_path.write_text(
            label_text,
            encoding="utf-8",
        )

        print(
            f"[{index}/{len(images)}] "
            f"Saved: {label_path.name}"
        )

    cv2.destroyAllWindows()

    print("\nAnnotation finished.")


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--category",
        required=True,
        choices=list(CATEGORY_MAP),
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Redo labels that already exist.",
    )

    args = parser.parse_args()

    annotate_category(
        category=args.category,
        force=args.force,
    )


if __name__ == "__main__":
    main()