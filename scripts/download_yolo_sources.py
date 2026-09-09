"""Download the two public CC BY 4.0 source datasets from Hugging Face."""

from __future__ import annotations

import argparse
from pathlib import Path

from huggingface_hub import snapshot_download


DATASETS = {
    "holes": "wargoninnovation/Garment_condition_holes",
    "spots": "wargoninnovation/Garment_condition_spots",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    for name, repository in DATASETS.items():
        snapshot_download(
            repo_id=repository,
            repo_type="dataset",
            local_dir=args.output / name,
        )


if __name__ == "__main__":
    main()
