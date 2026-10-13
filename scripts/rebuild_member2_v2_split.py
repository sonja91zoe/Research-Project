"""Build the clean 30-image Member 2 v2 pilot split.

This script uses only data/member2_v2/raw and raw_labels.  It never reads or
writes external_eval_v1 and does not change runtime thresholds.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


ROOT = Path("data/member2_v2")
CATEGORIES = ("hole_or_tear", "stain_or_spot", "clean")
SPLIT_IDS = {
    "train": ("001", "002", "003", "006", "007", "008"),
    "val": ("004", "009"),
    "test": ("005", "010"),
}


def source_name(category: str, identifier: str) -> str:
    prefix = {"hole_or_tear": "hole", "stain_or_spot": "stain", "clean": "clean"}[category]
    return f"{prefix}_{identifier}"


def validate_sources() -> dict[str, dict[str, list[str]]]:
    manifest: dict[str, dict[str, list[str]]] = {}
    for category in CATEGORIES:
        manifest[category] = {}
        for split, identifiers in SPLIT_IDS.items():
            names: list[str] = []
            for identifier in identifiers:
                stem = source_name(category, identifier)
                image = ROOT / "raw" / category / f"{stem}.png"
                label = ROOT / "raw_labels" / category / f"{stem}.txt"
                if not image.is_file() or not label.is_file():
                    raise FileNotFoundError(f"Missing paired source: {image} / {label}")
                label_text = label.read_text(encoding="utf-8")
                if category == "clean" and label_text:
                    raise ValueError(f"Clean label must be empty: {label}")
                if category == "hole_or_tear" and not label_text.startswith("0 "):
                    raise ValueError(f"Hole label must use class 0: {label}")
                if category == "stain_or_spot" and not label_text.startswith("1 "):
                    raise ValueError(f"Stain label must use class 1: {label}")
                names.append(stem)
            manifest[category][split] = names
    return manifest


def build(manifest: dict[str, dict[str, list[str]]]) -> None:
    for kind in ("images", "labels"):
        for split in SPLIT_IDS:
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
    totals = {split: sum(len(manifest[category][split]) for category in CATEGORIES) for split in SPLIT_IDS}
    assert totals == {"train": 18, "val": 6, "test": 6}, totals
    print(json.dumps({"manifest": manifest, "totals": totals}, indent=2))
    if args.apply:
        build(manifest)
        print("Rebuilt data/member2_v2/images and data/member2_v2/labels.")


if __name__ == "__main__":
    main()

