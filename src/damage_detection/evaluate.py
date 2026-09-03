"""Batch CLIP inference and evaluation for the Week 2 image dataset."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from src.damage_detection.damage import ClipBackend, DamageDetector


VISIBLE_STATE_TO_LABEL = {
    "hole_or_tear_visible": "hole_or_tear",
    "stain_or_spot_visible": "stain_or_spot",
    "no_clear_damage_visible": "no_damage",
}


def load_unique_images(manifest: Path, image_directory: Path) -> list[dict[str, str]]:
    """Create one image-only record per source photo; ignore claim verdicts."""
    with manifest.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    unique: dict[str, dict[str, str]] = {}
    for row in rows:
        state = row["actual_visual_state"]
        if state not in VISIBLE_STATE_TO_LABEL:
            continue
        source_id = row["source_image_id"]
        record = {
            "image_id": source_id,
            "file_name": row["file_name"],
            "expected_label": VISIBLE_STATE_TO_LABEL[state],
        }
        if source_id in unique and unique[source_id] != record:
            raise ValueError(f"Conflicting labels for source image {source_id}")
        unique[source_id] = record

    paths = {path.name: path for path in image_directory.rglob("*.jpg")}
    missing = sorted(record["file_name"] for record in unique.values() if record["file_name"] not in paths)
    if missing:
        raise FileNotFoundError(f"Missing {len(missing)} manifest images: {missing[:5]}")
    for record in unique.values():
        record["image_path"] = str(paths[record["file_name"]])
    return list(unique.values())


def calculate_metrics(rows: list[dict[str, object]]) -> dict[str, object]:
    evaluated = [row for row in rows if row["predicted_label"] != "uncertain"]
    labels = sorted({str(row["expected_label"]) for row in rows})
    per_class: dict[str, dict[str, float | int]] = {}
    for label in labels:
        tp = sum(row["expected_label"] == label and row["predicted_label"] == label for row in evaluated)
        fp = sum(row["expected_label"] != label and row["predicted_label"] == label for row in evaluated)
        fn = sum(row["expected_label"] == label and row["predicted_label"] != label for row in evaluated)
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
    detector = DamageDetector(ClipBackend())
    predictions: list[dict[str, object]] = []
    for index, record in enumerate(records, start=1):
        result = detector.detect(record["image_id"], record["image_path"])
        predictions.append({
            **record,
            "predicted_label": result.damage_type,
            "confidence": result.damage_confidence,
            "evidence_quality": result.evidence_quality,
            "needs_human_review": result.needs_human_review,
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
