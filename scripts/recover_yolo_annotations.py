"""Recover renamed Week 1 images' YOLO annotations by perceptual matching."""

from __future__ import annotations

import argparse
import csv
import math
import shutil
from pathlib import Path

from PIL import Image, ImageChops, ImageStat
from statistics import median


def perceptual_hash(path: Path, size: int = 24) -> tuple[bool, ...]:
    with Image.open(path) as image:
        values = list(
            image.convert("L").resize((size, size), Image.Resampling.LANCZOS).getdata()
        )
    threshold = median(values)
    return tuple(value > threshold for value in values)


def find_label(image_path: Path, labels_root: Path) -> Path | None:
    candidates = list(labels_root.rglob(f"{image_path.stem}.txt"))
    return candidates[0] if len(candidates) == 1 else None


def visual_rmse(left_path: Path, right_path: Path, size: int = 128) -> float:
    def load(path: Path) -> Image.Image:
        with Image.open(path) as image:
            return image.convert("RGB").resize((size, size), Image.Resampling.LANCZOS)

    difference = ImageChops.difference(load(left_path), load(right_path))
    channel_rms = ImageStat.Stat(difference).rms
    return math.sqrt(sum(value * value for value in channel_rms) / len(channel_rms))


def crop_from_yolo(image_path: Path, label_path: Path, output_path: Path, padding: float) -> int:
    boxes = []
    for line in label_path.read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if len(fields) >= 5:
            boxes.append(tuple(map(float, fields[1:5])))
    if not boxes:
        return 0

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
    return len(boxes)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selected", type=Path, required=True)
    parser.add_argument("--holes-images", type=Path, required=True)
    parser.add_argument("--holes-labels", type=Path, required=True)
    parser.add_argument("--spots-images", type=Path, required=True)
    parser.add_argument("--spots-labels", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-distance", type=int, default=8)
    parser.add_argument("--min-margin", type=int, default=2)
    parser.add_argument("--max-rmse", type=float, default=12.0)
    args = parser.parse_args()

    pools = {
        "hole": (args.holes_images, args.holes_labels),
        "spot": (args.spots_images, args.spots_labels),
    }
    indexes = {}
    for prefix, (images_root, _) in pools.items():
        files = list(images_root.rglob("*.jpg"))
        indexes[prefix] = [(path, perceptual_hash(path)) for path in files]
        print(f"Indexed {len(files)} {prefix} source images")

    rows = []
    labels_output = args.output / "labels"
    crops_output = args.output / "crops"
    for selected in sorted(args.selected.rglob("*.jpg")):
        prefix = "hole" if selected.name.startswith("hole_") else "spot"
        selected_hash = perceptual_hash(selected)
        ranked = sorted(
            ((sum(a != b for a, b in zip(selected_hash, source_hash)), source) for source, source_hash in indexes[prefix]),
            key=lambda item: item[0],
        )
        shortlist = ranked[:20]
        refined = sorted(
            ((visual_rmse(selected, source), distance, source) for distance, source in shortlist),
            key=lambda item: item[0],
        )
        best_rmse, best_distance, best_source = refined[0]
        second_rmse, second_distance, _ = refined[1]
        margin = second_distance - best_distance
        rmse_margin = second_rmse - best_rmse
        accepted = best_rmse <= args.max_rmse
        label_source = find_label(best_source, pools[prefix][1]) if accepted else None
        label_target = labels_output / f"{selected.stem}.txt"
        crop_target = crops_output / f"{selected.stem}_crop.jpg"
        box_count = 0
        if label_source is not None:
            labels_output.mkdir(parents=True, exist_ok=True)
            shutil.copy2(label_source, label_target)
            box_count = crop_from_yolo(selected, label_source, crop_target, padding=2.0)
        rows.append({
            "selected_file": selected.name,
            "source_file": best_source.name,
            "hash_distance": best_distance,
            "second_distance": second_distance,
            "distance_margin": margin,
            "pixel_rmse": round(best_rmse, 4),
            "second_pixel_rmse": round(second_rmse, 4),
            "pixel_rmse_margin": round(rmse_margin, 4),
            "match_accepted": accepted,
            "label_found": label_source is not None,
            "box_count": box_count,
        })

    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output / "source_file_mapping.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Accepted matches: {sum(row['match_accepted'] for row in rows)}/{len(rows)}")
    print(f"Labels recovered: {sum(row['label_found'] for row in rows)}/{len(rows)}")
    print(f"Crops created: {sum(row['box_count'] > 0 for row in rows)}/{len(rows)}")


if __name__ == "__main__":
    main()
