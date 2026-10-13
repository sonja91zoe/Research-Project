"""Read-only inference report for the frozen external_eval_v1 set."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


FIXED_MIN_USABLE_DAMAGE_CONFIDENCE = 0.10
FIXED_REVIEW_THRESHOLD = 0.15
REQUIRED_CASES = {"DAM-HOD-01", "DAM-HOD-02", "DAM-HOD-03"}


def prediction(result: object) -> dict[str, object] | None:
    boxes = result.boxes
    if boxes is None or len(boxes) == 0:
        return None
    index = int(boxes.conf.argmax().item())
    return {
        "damage_type": result.names[int(boxes.cls[index].item())],
        "confidence": round(float(boxes.conf[index].item()), 6),
        "review_required": float(boxes.conf[index].item()) < FIXED_REVIEW_THRESHOLD,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--external-root", type=Path, default=Path("external_eval_v1"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--image-size", type=int, default=512)
    args = parser.parse_args()

    from ultralytics import YOLO

    annotation_path = args.external_root / "annotations" / "images.csv"
    image_dir = args.external_root / "images"
    with annotation_path.open(newline="", encoding="utf-8") as handle:
        annotations = list(csv.DictReader(handle))
    model = YOLO(str(args.weights))
    rows: list[dict[str, object]] = []
    for annotation in annotations:
        image_id = annotation["image_id"]
        matches = list(image_dir.glob(f"{image_id}.*"))
        if len(matches) != 1:
            raise FileNotFoundError(f"Expected one image for {image_id}, found {matches}")
        result = model.predict(
            source=str(matches[0]),
            conf=FIXED_MIN_USABLE_DAMAGE_CONFIDENCE,
            imgsz=args.image_size,
            verbose=False,
        )[0]
        rows.append({
            "image_id": image_id,
            "ground_truth": annotation["damage_type_ground_truth"],
            "quality": annotation["image_quality_condition"],
            "relevant_region_visible": annotation["relevant_region_visible"],
            "prediction": prediction(result),
        })

    positives = [row for row in rows if row["image_id"] in REQUIRED_CASES]
    clean_controls = [
        row for row in rows
        if row["ground_truth"] == "no_visible_damage"
        and row["quality"] == "clear"
        and row["relevant_region_visible"] == "yes"
    ]
    report = {
        "purpose": "read-only external evaluation; not used for training, model selection, or threshold tuning",
        "fixed_thresholds": {
            "min_usable_damage_confidence": FIXED_MIN_USABLE_DAMAGE_CONFIDENCE,
            "review_threshold": FIXED_REVIEW_THRESHOLD,
        },
        "required_cases": positives,
        "clean_controls": {
            "count": len(clean_controls),
            "predictions": clean_controls,
            "false_positive_count": sum(row["prediction"] is not None for row in clean_controls),
        },
        "note": "DAM-HOD-02 is reported only as a framing/scale ablation of DAM-HOD-01, not an independent sample.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

