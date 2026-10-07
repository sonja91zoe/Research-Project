import csv

from PIL import Image

from src.damage_detection.evaluate import load_unique_images


def test_week4_traceability_columns_are_normalized_for_evaluation(tmp_path):
    images = tmp_path / "images"
    images.mkdir()
    Image.new("RGB", (8, 8), "white").save(images / "hole_001.jpg")
    manifest = tmp_path / "manifest.csv"
    with manifest.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["source_image_id", "file_name", "damage_type"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "source_image_id": "H001",
                "file_name": "hole_001.jpg",
                "damage_type": "hole_or_tear",
            }
        )

    rows = load_unique_images(manifest, images)

    assert rows[0]["image_id"] == "H001"
    assert rows[0]["expected_label"] == "hole_or_tear"
