"""Audit Week1 cases and produce a reproducible grouped Week3 review manifest."""
import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

LABELS = {"hole_or_tear": "hole_or_tear", "stain_or_spot": "stain_or_spot",
          "none": "no_damage", "uncertain_hole_or_tear": "uncertain",
          "uncertain_stain_or_spot": "uncertain"}


def prepare(rows, sample_groups=20, seed=32933):
    if sample_groups < 1:
        raise ValueError("sample_groups must be positive")
    if not rows:
        raise ValueError("empty dataset")
    seen = set()
    groups = set()
    for row in rows:
        for key in ("case_id", "source_image_id", "file_name", "damage_type",
                    "expected_verdict", "construction_method", "review_status"):
            if not row.get(key):
                raise ValueError(f"missing {key}")
        if row["case_id"] in seen:
            raise ValueError("duplicate case_id")
        if row["damage_type"] not in LABELS:
            raise ValueError("unknown damage label")
        if row["expected_verdict"] not in {"positive", "negative", "ambiguous"}:
            raise ValueError("unknown verdict")
        seen.add(row["case_id"])
        groups.add(row["source_image_id"])
    # Sort by salted digest: deterministic and independent of CSV row order.
    ranked = sorted(groups, key=lambda g: hashlib.sha256(f"{seed}:{g}".encode()).hexdigest())
    selected = set(ranked[:sample_groups])
    manifest = []
    for row in sorted(rows, key=lambda r: r["case_id"]):
        item = dict(row)
        issues = ["requires_independent_human_review"]
        if row["expected_verdict"] == "ambiguous":
            issues.append("variant_not_materialized_or_verified")
        if row["damage_type"] == "none":
            issues.append("clean_label_conflicts_with_positive_defect_source_pool")
        item.update(normalized_damage_type=LABELS[row["damage_type"]],
                    review_batch="sample" if row["source_image_id"] in selected else "remaining",
                    benchmark_eligible="false", audit_flags=";".join(issues))
        manifest.append(item)
    report = {"cases": len(rows), "source_images": len(groups), "seed": seed,
              "sample_source_images": len(selected),
              "verdict_counts": dict(Counter(r["expected_verdict"] for r in rows)),
              "sample_cases": sum(r["review_batch"] == "sample" for r in manifest),
              "benchmark_eligible_cases": 0,
              "note": "Review batches only; not an independent train/test split. Source labels remain provisional."}
    return manifest, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--sample-groups", type=int, default=20)
    args = parser.parse_args()
    with args.source.open(encoding="utf-8-sig", newline="") as handle:
        manifest, report = prepare(list(csv.DictReader(handle)), args.sample_groups)
    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output / "review_manifest.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(manifest[0]))
        writer.writeheader()
        writer.writerows(manifest)
    report["source_sha256"] = hashlib.sha256(args.source.read_bytes()).hexdigest()
    (args.output / "audit.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
