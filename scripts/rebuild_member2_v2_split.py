"""Build the clean 250-image Member 2 v2 training split.

This script uses only data/member2_v2/raw and raw_labels. It never reads or
writes external_eval_v1 and does not change runtime thresholds.
"""

from __future__ import annotations

import argparse
import json
import random
import shutil
from pathlib import Path


ROOT = Path("data/member2_v2")
CATEGORIES = ("hole_or_tear", "stain_or_spot", "clean")
CATEGORY_COUNTS = {
    "hole_or_tear": 90,
    "stain_or_spot": 75,
    "clean": 85,
}
SPLIT_COUNTS = {
    "hole_or_tear": {"train": 63, "val": 14, "test": 13},
    "stain_or_spot": {"train": 52, "val": 12, "test": 11},
    "clean": {"train": 59, "val": 13, "test": 13},
}
SPLIT_ORDER = ("train", "val", "test")
SEED = "member2-v2-250-2026-10-17"


def source_name(category: str, identifier: str) -> str:
    prefix = {
        "hole_or_tear": "hole",
        "stain_or_spot": "stain",
        "clean": "clean",
    }[category]
    return f"{prefix}_{identifier}"


def split_ids(category: str) -> dict[str, tuple[str, ...]]:
    expected = [f"{identifier:03d}" for identifier in range(1, CATEGORY_COUNTS[category] + 1)]
    identifiers = expected.copy()
    random.Random(f"{SEED}:{category}").shuffle(identifiers)

    split_map: dict[str, tuple[str, ...]] = {}
    cursor = 0
    for split in SPLIT_ORDER:
        count = SPLIT_COUNTS[category][split]
        split_map[split] = tuple(identifiers[cursor : cursor + count])
        cursor += count

    observed = [identifier for split in SPLIT_ORDER for identifier in split_map[split]]
    if len(observed) != len(set(observed)) or set(observed) != set(expected):
        raise ValueError(f"Split IDs must contain every expected identifier exactly once for {category}.")
    if cursor != len(expected):
        raise ValueError(f"Split count does not cover all expected identifiers for {category}.")
    return split_map


def validate_damage_label(label: Path, expected_class: int) -> None:
    lines = [line.strip() for line in label.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        raise ValueError(f"Damage label must not be empty: {label}")
    for line in lines:
        fields = line.split()
        if len(fields) != 5 or fields[0] != str(expected_class):
            raise ValueError(f"Invalid class or field count in {label}: {line!r}")
        x_center, y_center, width, height = map(float, fields[1:])
        if not (0 <= x_center <= 1 and 0 <= y_center <= 1 and 0 < width <= 1 and 0 < height <= 1):
            raise ValueError(f"YOLO values out of range in {label}: {line!r}")
        if x_center - width / 2 < 0 or x_center + width / 2 > 1:
            raise ValueError(f"YOLO x box extends outside image in {label}: {line!r}")
        if y_center - height / 2 < 0 or y_center + height / 2 > 1:
            raise ValueError(f"YOLO y box extends outside image in {label}: {line!r}")


def validate_sources() -> dict[str, dict[str, list[str]]]:
    manifest: dict[str, dict[str, list[str]]] = {}
    expected_class = {"hole_or_tear": 0, "stain_or_spot": 1}

    for category in CATEGORIES:
        manifest[category] = {}
        for split, identifiers in split_ids(category).items():
            names: list[str] = []
            for identifier in identifiers:
                stem = source_name(category, identifier)
                image = ROOT / "raw" / category / f"{stem}.png"
                label = ROOT / "raw_labels" / category / f"{stem}.txt"
                if not image.is_file() or not label.is_file():
                    raise FileNotFoundError(f"Missing paired source: {image} / {label}")
                if category == "clean":
                    if label.read_text(encoding="utf-8").strip():
                        raise ValueError(f"Clean label must be empty: {label}")
                else:
                    validate_damage_label(label, expected_class[category])
                names.append(stem)
            manifest[category][split] = names
    return manifest


def build(manifest: dict[str, dict[str, list[str]]]) -> None:
    for kind in ("images", "labels"):
        for split in SPLIT_ORDER:
            destination = ROOT / kind / split
            if destination.exists():
                shutil.rmtree(destination)
            destination.mkdir(parents=True)
    for category, split_map in manifest.items():
        for split, stems in split_map.items():
            for stem in stems:
                shutil.copy2(ROOT / "raw" / category / f"{stem}.png", ROOT / "images" / split / f"{stem}.png")
                shutil.copy2(ROOT / "raw_labels" / category / f"{stem}.txt", ROOT / "labels" / split / f"{stem}.txt")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="replace the existing images/ and labels/ split directories")
    args = parser.parse_args()

    manifest = validate_sources()
    totals = {
        split: sum(len(manifest[category][split]) for category in CATEGORIES)
        for split in SPLIT_ORDER
    }
    assert totals == {"train": 174, "val": 39, "test": 37}, totals
    print(json.dumps({"manifest": manifest, "totals": totals}, indent=2))
    if args.apply:
        build(manifest)
        print("Rebuilt data/member2_v2/images and data/member2_v2/labels with 250 images.")


if __name__ == "__main__":
    main()
