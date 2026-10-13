"""Write reproducible validation and test metrics for the Member 2 v2 run."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def metric_values(metrics: object) -> dict[str, float]:
    box = metrics.box
    return {
        "precision": float(box.mp),
        "recall": float(box.mr),
        "mAP50": float(box.map50),
        "mAP50_95": float(box.map),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--image-size", type=int, default=512)
    args = parser.parse_args()

    from ultralytics import YOLO

    model = YOLO(str(args.weights))
    report = {
        "weights": str(args.weights),
        "data": str(args.data),
        "image_size": args.image_size,
        "validation": metric_values(model.val(data=str(args.data), split="val", imgsz=args.image_size)),
        "test": metric_values(model.val(data=str(args.data), split="test", imgsz=args.image_size)),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

