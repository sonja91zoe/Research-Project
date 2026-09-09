"""Evaluate trained YOLO weights on the held-out 70-image Week 2 set."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from src.damage_detection.evaluate import calculate_metrics, load_unique_images
from src.damage_detection.yolo import YoloBackend


def calculate_review_metrics(
    rows: list[dict[str, object]], review_threshold: float
) -> dict[str, object]:
    review_free = [
        row
        for row in rows
        if row["predicted_label"] != "uncertain"
        and float(row["confidence"]) >= review_threshold
    ]
    correct = sum(
        row["expected_label"] == row["predicted_label"] for row in review_free
    )
    return {
        "review_threshold": review_threshold,
        "review_free_images": len(review_free),
        "human_review_images": len(rows) - len(review_free),
        "automation_coverage": len(review_free) / len(rows) if rows else 0.0,
        "accuracy_on_review_free_predictions": (
            correct / len(review_free) if review_free else None
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--images", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--confidence", type=float, default=0.01)
    parser.add_argument("--review-threshold", type=float, default=0.70)
    args = parser.parse_args()

    records = load_unique_images(args.manifest, args.images)
    backend = YoloBackend(args.weights, confidence_threshold=args.confidence)
    predictions: list[dict[str, object]] = []
    for index, record in enumerate(records, start=1):
        result = backend.predict(Path(record["image_path"]))
        predictions.append(
            {
                "image_id": record["image_id"],
                "file_name": record["file_name"],
                "expected_label": record["expected_label"],
                "predicted_label": result.damage_type,
                "confidence": result.confidence,
                "needs_human_review": (
                    result.damage_type == "uncertain"
                    or result.confidence < args.review_threshold
                ),
                "rationale": result.rationale,
                "model_name": args.weights.name,
            }
        )
        print(f"[{index}/{len(records)}] {record['file_name']}: {result.damage_type}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / "week2_yolo_predictions.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(predictions[0]))
        writer.writeheader()
        writer.writerows(predictions)
    metrics = calculate_metrics(predictions)
    metrics["model_name"] = args.weights.name
    metrics["confidence_threshold"] = args.confidence
    metrics.update(calculate_review_metrics(predictions, args.review_threshold))
    (args.output_dir / "week2_yolo_metrics.json").write_text(
        json.dumps(metrics, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
