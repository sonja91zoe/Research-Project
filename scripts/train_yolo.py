"""Fine-tune the free local YOLO detector for the two Week 1 damage classes."""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--model", default="yolo11n.pt")
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--image-size", type=int, default=512)
    parser.add_argument("--output", type=Path, default=Path("artifacts/member2_yolo"))
    args = parser.parse_args()

    from ultralytics import YOLO

    model = YOLO(args.model)
    model.train(
        data=str(args.data.resolve()),
        epochs=args.epochs,
        imgsz=args.image_size,
        project=str(args.output.resolve()),
        name="damage_detector",
        exist_ok=True,
    )


if __name__ == "__main__":
    main()
