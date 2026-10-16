"""Build the clean 150-image Member 2 v2 training split.

This script uses only data/member2_v2/raw and raw_labels. It never reads or
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
    "train": (
        "001", "002", "003", "006", "007", "008",
        "011", "012", "013", "016", "017", "018",
        "021", "022", "023", "026", "027", "028",
        "031", "032", "033", "036", "037", "038",
        "041", "042", "043", "046", "047", "048",
    ),
    "val": (
        "004", "009",
        "014", "019", "024", "029", "034", "039", "044", "049",
    ),
    "test": (
        "005", "010",
        "015", "020", "025", "030", "035", "040", "045", "050",
    ),
}


def source_name(category: str, identifier: str) -> str:
    prefix = {
        "hole_or_tear": "hole",
        "stain_or_spot": "stain",
        "clean": "clean",
    }[category]
    return f"{prefix}_{identifier}"


def validate_split_ids() -> None:
    expected = {f"{identifier:03d}" for identifier in range(1, 51)}
    observed = [identifier for identifiers in SPLIT_IDS.values() for identifier in identifiers]
    if len(observed) != len(set(observed)) or set(observed) != expected:
        raise ValueError("Split IDs must contain every identifier 001-050 exactly once.")
    counts = {split: len(identifiers) for split, identifiers in SPLIT_IDS.items()}
    if counts != {"train": 30, "val": 10, "test": 10}:
        raise ValueError(f"Expected per-class 30/10/10 split, received {counts}.")


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
    validate_split_ids()
    manifest: dict[str, dict[str, list[str]]] = {}
    expected_class = {"hole_or_tear": 0, "stain_or_spot": 1}
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
    totals = {
        split: sum(len(manifest[category][split]) for category in CATEGORIES)
        for split in SPLIT_IDS
    }
    assert totals == {"train": 90, "val": 30, "test": 30}, totals
    print(json.dumps({"manifest": manifest, "totals": totals}, indent=2))
    if args.apply:
        build(manifest)
        print("Rebuilt data/member2_v2/images and data/member2_v2/labels with 150 images.")


if __name__ == "__main__":
    main()
