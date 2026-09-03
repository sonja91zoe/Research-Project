"""Batch CLIP inference and evaluation for the Week 2 image dataset."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from PIL import Image

from src.damage_detection.damage import ClipBackend


def create_yolo_crop(
    image_path: Path, label_path: Path, output_path: Path, padding: float = 2.0
) -> Path | None:
    boxes = []
    for line in label_path.read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if len(fields) >= 5:
            boxes.append(tuple(map(float, fields[1:5])))
    if not boxes:
        return None
    with Image.open(image_path) as image:
        width, height = image.size
        left = min((cx - bw / 2) * width for cx, cy, bw, bh in boxes)
        top = min((cy - bh / 2) * height for cx, cy, bw, bh in boxes)
        right = max((cx + bw / 2) * width for cx, cy, bw, bh in boxes)
        bottom = max((cy + bh / 2) * height for cx, cy, bw, bh in boxes)
        box_width, box_height = right - left, bottom - top
        pad_x = max(box_width * padding, width * 0.03)
        pad_y = max(box_height * padding, height * 0.03)
        crop_box = (
            max(0, int(left - pad_x)),
            max(0, int(top - pad_y)),
            min(width, int(right + pad_x)),
            min(height, int(bottom + pad_y)),
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        image.crop(crop_box).convert("RGB").save(output_path, "JPEG", quality=90)
    return output_path


def load_unique_images(manifest: Path, image_directory: Path) -> list[dict[str, str]]:
    """Load the dedicated image-only Week 2 manifest."""
    with manifest.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    paths = {path.name: path for path in image_directory.rglob("*.jpg")}
    missing = sorted(row["file_name"] for row in rows if row["file_name"] not in paths)
    if missing:
        raise FileNotFoundError(f"Missing {len(missing)} manifest images: {missing[:5]}")
    for row in rows:
        row["image_path"] = str(paths[row["file_name"]])
        crop_value = row.get("crop_path", "")
        if crop_value:
            crop_path = manifest.parent / crop_value
            row["crop_path"] = str(crop_path) if crop_path.is_file() else ""
        label_value = row.get("yolo_label_path", "")
        if label_value:
            label_path = manifest.parent / label_value
            if not label_path.is_file():
                raise FileNotFoundError(f"YOLO label not found: {label_path}")
            row["yolo_label_path"] = str(label_path)
    return rows


def calculate_metrics(rows: list[dict[str, object]]) -> dict[str, object]:
    evaluated = [row for row in rows if row["predicted_label"] != "uncertain"]
    labels = sorted({str(row["expected_label"]) for row in rows})
    per_class: dict[str, dict[str, float | int]] = {}
    for label in labels:
        tp = sum(row["expected_label"] == label and row["predicted_label"] == label for row in rows)
        fp = sum(row["expected_label"] != label and row["predicted_label"] == label for row in rows)
        fn = sum(row["expected_label"] == label and row["predicted_label"] != label for row in rows)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[label] = {"precision": precision, "recall": recall, "f1": f1, "support": sum(row["expected_label"] == label for row in rows)}
    correct = sum(row["expected_label"] == row["predicted_label"] for row in evaluated)
    return {
        "total_images": len(rows),
        "evaluated_images": len(evaluated),
        "reviewed_images": len(rows) - len(evaluated),
        "coverage": len(evaluated) / len(rows) if rows else 0.0,
        "accuracy_on_automatic_predictions": correct / len(evaluated) if evaluated else 0.0,
        "end_to_end_accuracy": sum(row["expected_label"] == row["predicted_label"] for row in rows) / len(rows) if rows else 0.0,
        "macro_f1": sum(item["f1"] for item in per_class.values()) / len(per_class) if per_class else 0.0,
        "per_class": per_class,
        "expected_counts": dict(Counter(str(row["expected_label"]) for row in rows)),
        "predicted_counts": dict(Counter(str(row["predicted_label"]) for row in rows)),
        "warning": "Metrics cover only classes present in the image-only ground truth.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the free CLIP Week 2 evaluation")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--images", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/member2_week2"))
    args = parser.parse_args()

    records = load_unique_images(args.manifest, args.images)
    backend = ClipBackend()
    predictions: list[dict[str, object]] = []
    for index, record in enumerate(records, start=1):
        views = [Path(record["image_path"])]
        crop_path = Path(record["crop_path"]) if record.get("crop_path") else None
        if crop_path is None and record.get("yolo_label_path"):
            crop_path = create_yolo_crop(
                Path(record["image_path"]),
                Path(record["yolo_label_path"]),
                args.output_dir / "crops" / f"{record['image_id']}_crop.jpg",
            )
        if crop_path is not None:
            views.append(crop_path)
        result = backend.predict_many(views)
        predictions.append({
            **record,
            "predicted_label": result.damage_type,
            "confidence": result.confidence,
            "evidence_quality": "good",
            "needs_human_review": result.damage_type == "uncertain",
            "rationale": result.rationale,
            "model_name": ClipBackend.MODEL_NAME,
        })
        print(f"[{index}/{len(records)}] {record['file_name']}: {result.damage_type}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    predictions_path = args.output_dir / "week2_predictions.csv"
    with predictions_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(predictions[0]))
        writer.writeheader()
        writer.writerows(predictions)
    metrics = calculate_metrics(predictions)
    (args.output_dir / "week2_metrics.json").write_text(
        json.dumps(metrics, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
