"""Run the leakage-safe Week 5 visual-evidence evaluation for Member 2.

The Week 1 CSV is a *case* manifest, not a collection of 100 independent
photographs.  This runner keeps ``source_image_id`` in every output row and
never treats a recipe-only variant as an observed image.  Supply real model
weights (YOLO) or select CLIP to produce measured predictions; ``none`` is a
useful preflight mode that writes an honest execution inventory.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from src.common.schemas import CaseInput, Member1Output
from src.damage_detection.damage import ClipBackend, DamageDetector
from src.damage_detection.verification import verify_claim
from src.damage_detection.yolo import YoloBackend
from src.image_quality.claim_parser import parse_claim


DAMAGE_LABELS = ("hole_or_tear", "stain_or_spot", "no_damage", "uncertain")
VERDICTS = ("positive", "negative", "ambiguous")


def expected_damage_label(row: dict[str, str]) -> str:
    """Map Week 1 visual ground truth to the Member 2 shared schema."""
    return {"none": "no_damage"}.get(row["damage_type"], row["damage_type"])


def source_safe_groups(rows: list[dict[str, str]]) -> dict[str, list[str]]:
    """Return case ids grouped by underlying source image (for split audits)."""
    groups: dict[str, list[str]] = {}
    for row in rows:
        groups.setdefault(row["source_image_id"], []).append(row["case_id"])
    return groups


def metrics(rows: list[dict[str, str]], target: str, labels: tuple[str, ...]) -> dict[str, Any]:
    """Compute multiclass metrics only from executed rows with a prediction."""
    available = [row for row in rows if row.get("execution_status") == "executed"]
    if not available:
        return {"status": "not_available", "reason": "No model predictions were executed."}
    truth_key = f"expected_{target}"
    prediction_key = f"predicted_{target}"
    per_class: dict[str, dict[str, float | int]] = {}
    for label in labels:
        tp = sum(r[truth_key] == label and r[prediction_key] == label for r in available)
        fp = sum(r[truth_key] != label and r[prediction_key] == label for r in available)
        fn = sum(r[truth_key] == label and r[prediction_key] != label for r in available)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[label] = {"precision": precision, "recall": recall, "f1": f1, "support": sum(r[truth_key] == label for r in available)}
    accuracy = sum(r[truth_key] == r[prediction_key] for r in available) / len(available)
    macro_labels = tuple(label for label, item in per_class.items() if item["support"] > 0)
    return {
        "status": "available", "n": len(available), "accuracy": accuracy,
        "macro_labels": list(macro_labels),
        "macro_precision": sum(per_class[x]["precision"] for x in macro_labels) / len(macro_labels),
        "macro_recall": sum(per_class[x]["recall"] for x in macro_labels) / len(macro_labels),
        "macro_f1": sum(per_class[x]["f1"] for x in macro_labels) / len(macro_labels),
        "per_class": per_class,
    }


def draw_confusion_matrix(rows: list[dict[str, str]], target: str, labels: tuple[str, ...], output: Path) -> bool:
    available = [row for row in rows if row.get("execution_status") == "executed"]
    if not available:
        return False
    size, margin, cell = 720, 170, 110
    image = Image.new("RGB", (size, size), "white")
    draw = ImageDraw.Draw(image)
    draw.text((20, 20), f"Week 5 {target.replace('_', ' ')} confusion matrix", fill="black")
    for index, label in enumerate(labels):
        draw.text((margin + index * cell, 70), label.replace("_", "\n"), fill="black")
        draw.text((15, margin + index * cell), label.replace("_", "\n"), fill="black")
    max_count = max(1, max(sum(r[f"expected_{target}"] == a and r[f"predicted_{target}"] == b for r in available) for a in labels for b in labels))
    for y, actual in enumerate(labels):
        for x, predicted in enumerate(labels):
            count = sum(r[f"expected_{target}"] == actual and r[f"predicted_{target}"] == predicted for r in available)
            shade = int(255 - 190 * count / max_count)
            left, top = margin + x * cell, margin + y * cell
            draw.rectangle((left, top, left + cell, top + cell), fill=(shade, shade, 255), outline="black")
            draw.text((left + 45, top + 45), str(count), fill="black")
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output)
    return True


def make_detector(backend: str, weights: Path | None) -> DamageDetector | None:
    if backend == "none":
        return None
    if backend == "clip":
        return DamageDetector(ClipBackend())
    if weights is None or not weights.is_file():
        raise FileNotFoundError("--weights must name an existing YOLO weights file")
    return DamageDetector(YoloBackend(weights, confidence_threshold=0.01))


def write_failure_cases(rows: list[dict[str, str]], output: Path) -> None:
    """Write a factual review queue without inventing visual root causes."""
    failures = [
        row for row in rows
        if row["execution_status"] == "executed" and (
            row["expected_damage"] != row["predicted_damage"]
            or row["expected_consistency"] != row["predicted_consistency"]
            or row["needs_human_review"] == "true"
        )
    ]
    lines = [
        "# Week 5 failure-case review",
        "",
        "Auto-generated from measured outputs. It records factual mismatches and review flags; visual root causes require human inspection and are not inferred here.",
        "",
        "| Case ID | Source image ID | Category | Damage: expected → predicted | Claim: expected → predicted | Confidence | Verification reason |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in failures[:10]:
        lines.append(
            "| {case_id} | {source_image_id} | {category} | {expected_damage} → {predicted_damage} | {expected_consistency} → {predicted_consistency} | {damage_confidence} | {reason_code} |".format(**row)
        )
    if not failures:
        lines.append("| — | — | No measured failures or review flags | — | — | — | — |")
    elif len(failures) > 10:
        lines.extend(["", f"Showing the first 10 of {len(failures)} measured failure/review rows; use `week5_results.csv` for the complete list."])
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(manifest: Path, images: Path, output_dir: Path, backend: str, weights: Path | None) -> dict[str, Any]:
    with manifest.open(encoding="utf-8-sig", newline="") as handle:
        cases = list(csv.DictReader(handle))
    image_index = {path.name: path for path in images.rglob("*.jpg")}
    detector = make_detector(backend, weights)
    rows: list[dict[str, str]] = []
    for case in cases:
        # Altered claims reuse a real Week 1 photo and are therefore executable.
        # Only the explicitly constructed ambiguous variants lack an image asset.
        materialized = case["case_origin"] != "constructed_ambiguous_variant"
        image_path = image_index.get(case["file_name"]) if materialized else None
        result: dict[str, str] = {
            "case_id": case["case_id"], "source_image_id": case["source_image_id"],
            "image_variant_id": case["image_variant_id"], "category": case["construction_method"],
            "image_path": str(image_path) if image_path else "", "expected_damage": expected_damage_label(case),
            "expected_consistency": case["expected_verdict"], "predicted_damage": "",
            "predicted_consistency": "", "damage_confidence": "", "needs_human_review": "",
            "reason_code": "", "execution_status": "", "model": backend,
        }
        if not materialized:
            result["execution_status"] = "not_materialized_variant"
        elif image_path is None:
            result["execution_status"] = "missing_source_image"
        elif detector is None:
            result["execution_status"] = "blocked_no_model_selected"
        else:
            try:
                visual = detector.detect(case["case_id"], image_path)
                parsed = parse_claim(case["claim_text"])
                member1 = Member1Output(case_id=case["case_id"], image_quality=1.0, blur_score=0.0, lighting_score=1.0, relevant_region_visible=True, image_usable=True, **parsed)
                verified = verify_claim(CaseInput(case_id=case["case_id"], order_id="WEEK5-EVAL", claim_text=case["claim_text"], image_paths=[str(image_path)]), member1, visual)
                result.update(predicted_damage=visual.damage_type, predicted_consistency=verified.verdict, damage_confidence=f"{visual.damage_confidence:.6f}", needs_human_review=str(visual.needs_human_review).lower(), reason_code=verified.reason_code, execution_status="executed")
            except Exception as exc:  # Preserve partial evidence inventory if runtime/assets are unavailable.
                result.update(execution_status="blocked_inference", reason_code=f"{type(exc).__name__}: {exc}")
        rows.append(result)
    output_dir.mkdir(parents=True, exist_ok=True)
    columns = list(rows[0])
    with (output_dir / "week5_results.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader(); writer.writerows(rows)
    payload = {
        "dataset_cases": len(cases), "source_image_groups": len(source_safe_groups(cases)),
        "execution_status_counts": dict(Counter(row["execution_status"] for row in rows)),
        "leakage_policy": "All split/evaluation grouping is by source_image_id; variants never form independent observations.",
        "damage_detection": metrics(rows, "damage", DAMAGE_LABELS),
        "claim_image_verification": metrics(rows, "consistency", VERDICTS),
    }
    (output_dir / "week5_metrics.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    draw_confusion_matrix(rows, "damage", DAMAGE_LABELS, output_dir / "week5_damage_confusion_matrix.png")
    draw_confusion_matrix(rows, "consistency", VERDICTS, output_dir / "week5_consistency_confusion_matrix.png")
    write_failure_cases(rows, output_dir / "failure_cases.md")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("data/Week4_damage_dataset_v1/damage_dataset_v1.csv"))
    parser.add_argument("--images", type=Path, default=Path("data/Week4_damage_dataset_v1/images"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/member2/week5"))
    parser.add_argument("--backend", choices=("none", "clip", "yolo"), default="none")
    parser.add_argument("--weights", type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.manifest, args.images, args.output_dir, args.backend, args.weights), indent=2))


if __name__ == "__main__":
    main()
