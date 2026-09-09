"""Member 1 Week 3 evaluation script."""

from pathlib import Path
import csv

from src.image_quality.quality import assess_image_quality


LABEL_FILE = Path("data/member1/image_quality_labels_v1.csv")


def load_labels() -> list[dict]:
    """Load manually labelled image-quality data."""
    with LABEL_FILE.open("r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        return list(reader)


def evaluate_dataset() -> list[dict]:
    """
    Compare manual labels with Image Quality Module V1 predictions.

    Returns one structured evaluation record per image.
    """
    dataset = load_labels()
    results = []

    for row in dataset:
        image_path = row["image_path"]
        relevant_region_visible = (
            row["relevant_region_visible"].lower() == "true"
        )

        prediction = assess_image_quality(
            image_path,
            relevant_region_visible=relevant_region_visible,
        )

        manual_usable = row["image_usable"].lower() == "true"

        blur_correct = (
            prediction["blur_label"] == row["blur_label"]
        )

        lighting_correct = (
            prediction["lighting_label"] == row["lighting_label"]
        )

        usability_correct = (
            prediction["image_usable"] == manual_usable
        )

        results.append(
            {
                "case_id": row["case_id"],
                "image_path": image_path,
                "manual_blur": row["blur_label"],
                "predicted_blur": prediction["blur_label"],
                "blur_correct": blur_correct,
                "manual_lighting": row["lighting_label"],
                "predicted_lighting": prediction["lighting_label"],
                "lighting_correct": lighting_correct,
                "manual_usable": manual_usable,
                "predicted_usable": prediction["image_usable"],
                "usability_correct": usability_correct,
                "usability_reason": prediction["usability_reason"],
            }
        )

    return results


def print_summary(results: list[dict]) -> None:
    """Print evaluation accuracy and failure cases."""
    total = len(results)

    blur_correct = sum(
        result["blur_correct"] for result in results
    )

    lighting_correct = sum(
        result["lighting_correct"] for result in results
    )

    usability_correct = sum(
        result["usability_correct"] for result in results
    )

    print("\n=== Member 1 Week 3 Evaluation ===")
    print(f"Total images: {total}")

    print(
        f"Blur accuracy: "
        f"{blur_correct}/{total} "
        f"({blur_correct / total:.1%})"
    )

    print(
        f"Lighting accuracy: "
        f"{lighting_correct}/{total} "
        f"({lighting_correct / total:.1%})"
    )

    print(
        f"Usability accuracy: "
        f"{usability_correct}/{total} "
        f"({usability_correct / total:.1%})"
    )

    print("\n=== Failure Cases ===")

    failure_count = 0

    for result in results:
        if not (
            result["blur_correct"]
            and result["lighting_correct"]
            and result["usability_correct"]
        ):
            failure_count += 1

            print(f"\nCase: {result['case_id']}")
            print(f"Image: {result['image_path']}")

            if not result["blur_correct"]:
                print(
                    "Blur mismatch: "
                    f"manual={result['manual_blur']}, "
                    f"predicted={result['predicted_blur']}"
                )

            if not result["lighting_correct"]:
                print(
                    "Lighting mismatch: "
                    f"manual={result['manual_lighting']}, "
                    f"predicted={result['predicted_lighting']}"
                )

            if not result["usability_correct"]:
                print(
                    "Usability mismatch: "
                    f"manual={result['manual_usable']}, "
                    f"predicted={result['predicted_usable']}"
                )

    if failure_count == 0:
        print("No failure cases found.")


if __name__ == "__main__":
    evaluation_results = evaluate_dataset()
    print_summary(evaluation_results)