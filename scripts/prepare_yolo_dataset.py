"""Build a two-class YOLO dataset while excluding the held-out Week 2 images."""

from __future__ import annotations

import argparse
import csv
import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SourceDataset:
    root: Path
    class_id: int


def source_group(filename: str) -> str:
    """Group Roboflow augmentations that came from the same original image."""
    return Path(filename).stem.split(".rf.", 1)[0]


def held_out_groups(mapping_path: Path) -> set[str]:
    with mapping_path.open(encoding="utf-8-sig", newline="") as handle:
        return {source_group(row["source_file"]) for row in csv.DictReader(handle)}


def remap_label(source: Path, target: Path, class_id: int) -> None:
    lines = []
    for line in source.read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if len(fields) >= 5:
            fields[0] = str(class_id)
            lines.append(" ".join(fields))
    target.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def prepare_dataset(
    sources: list[SourceDataset], output: Path, excluded_groups: set[str]
) -> dict[str, int]:
    counts = {"train": 0, "val": 0, "excluded": 0}
    for split_name, source_split in (("train", "train"), ("val", "valid")):
        images_out = output / split_name / "images"
        labels_out = output / split_name / "labels"
        images_out.mkdir(parents=True, exist_ok=True)
        labels_out.mkdir(parents=True, exist_ok=True)
        for source in sources:
            images = source.root / source_split / "images"
            labels = source.root / source_split / "labels"
            for image in sorted(images.glob("*.jpg")):
                if source_group(image.name) in excluded_groups:
                    counts["excluded"] += 1
                    continue
                label = labels / f"{image.stem}.txt"
                if not label.is_file():
                    raise FileNotFoundError(f"Missing label for {image}")
                prefix = "hole" if source.class_id == 0 else "spot"
                target_name = f"{prefix}_{image.name}"
                shutil.copy2(image, images_out / target_name)
                remap_label(label, labels_out / f"{Path(target_name).stem}.txt", source.class_id)
                counts[split_name] += 1

    (output / "data.yaml").write_text(
        f"path: {output.resolve().as_posix()}\ntrain: train/images\nval: val/images\n"
        "names:\n  0: hole_or_tear\n  1: stain_or_spot\n",
        encoding="utf-8",
    )
    return counts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--holes", type=Path, required=True)
    parser.add_argument("--spots", type=Path, required=True)
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    counts = prepare_dataset(
        [SourceDataset(args.holes, 0), SourceDataset(args.spots, 1)],
        args.output,
        held_out_groups(args.mapping),
    )
    print(counts)


if __name__ == "__main__":
    main()
