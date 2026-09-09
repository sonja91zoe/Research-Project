from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from pydantic import ValidationError

from src.common.schemas import Member2Output
from src.damage_detection.damage import (
    ClipBackend,
    DamageDetector,
    DamagePrediction,
    FixedBackend,
)
from src.damage_detection.evaluate import calculate_metrics, create_yolo_crop
from src.damage_detection.evaluate_yolo import calculate_review_metrics
from src.damage_detection.yolo import YoloBackend
from scripts.prepare_yolo_dataset import (
    SourceDataset,
    normalize_annotation,
    prepare_dataset,
    source_group,
)


class Member2DamageTests(unittest.TestCase):
    @staticmethod
    def make_image(directory: str) -> Path:
        image = Path(directory) / "garment.jpg"
        image.write_bytes(b"week2-test-image")
        return image

    def test_hole_prediction_uses_shared_member2_schema(self):
        with TemporaryDirectory() as directory:
            backend = FixedBackend(DamagePrediction("hole_or_tear", 0.91, "Visible opening."))
            result = DamageDetector(backend).detect("DDV1-001", self.make_image(directory))
            self.assertIsInstance(result, Member2Output)
            self.assertTrue(result.damage_detected)
            self.assertEqual(result.damage_type, "hole_or_tear")
            self.assertIsNone(result.claim_image_consistency)
            self.assertFalse(result.needs_human_review)

    def test_poor_evidence_is_uncertain_and_reviewed(self):
        with TemporaryDirectory() as directory:
            backend = FixedBackend(DamagePrediction("stain_or_spot", 0.99, "Not called."))
            result = DamageDetector(backend).detect(
                "DDV1-071", self.make_image(directory), evidence_quality="poor"
            )
            self.assertFalse(result.damage_detected)
            self.assertEqual(result.damage_type, "uncertain")
            self.assertTrue(result.needs_human_review)

    def test_low_confidence_routes_to_review(self):
        with TemporaryDirectory() as directory:
            backend = FixedBackend(DamagePrediction("no_damage", 0.55, "No clear defect."))
            result = DamageDetector(backend).detect("DDV1-041", self.make_image(directory))
            self.assertEqual(result.damage_type, "no_damage")
            self.assertTrue(result.needs_human_review)

    def test_missing_image_is_rejected(self):
        backend = FixedBackend(DamagePrediction("no_damage", 0.9, "No defect."))
        with self.assertRaises(FileNotFoundError):
            DamageDetector(backend).detect("DDV1-X", "missing.jpg")

    def test_schema_rejects_inconsistent_damage_state(self):
        with self.assertRaises(ValidationError):
            Member2Output(
                case_id="DDV1-X",
                damage_detected=True,
                damage_type="no_damage",
                damage_confidence=0.9,
            )

    def test_schema_normalizes_team_legacy_label(self):
        output = Member2Output(
            case_id="REFUND_001",
            damage_detected=True,
            damage_type="tear",
            damage_confidence=0.9,
        )
        self.assertEqual(output.damage_type, "hole_or_tear")

    def test_clip_backend_maps_prompt_without_downloading_model(self):
        def fake_classifier(image_path, candidate_labels):
            stain_prompts = set(ClipBackend.LABEL_PROMPTS["stain_or_spot"])
            return [
                {"label": label, "score": 0.24 if label in stain_prompts else 0.0467}
                for label in candidate_labels
            ]

        with TemporaryDirectory() as directory:
            prediction = ClipBackend(classifier=fake_classifier).predict(
                self.make_image(directory)
            )
            self.assertEqual(prediction.damage_type, "stain_or_spot")
            self.assertGreater(prediction.confidence, 0.70)

    def test_clip_backend_marks_close_scores_uncertain(self):
        def fake_classifier(image_path, candidate_labels):
            return [{"label": label, "score": 1 / len(candidate_labels)} for label in candidate_labels]

        with TemporaryDirectory() as directory:
            prediction = ClipBackend(classifier=fake_classifier).predict(
                self.make_image(directory)
            )
            self.assertEqual(prediction.damage_type, "uncertain")

    def test_metrics_exclude_uncertain_from_automatic_accuracy(self):
        rows = [
            {"expected_label": "hole_or_tear", "predicted_label": "hole_or_tear"},
            {"expected_label": "stain_or_spot", "predicted_label": "hole_or_tear"},
            {"expected_label": "stain_or_spot", "predicted_label": "uncertain"},
        ]
        metrics = calculate_metrics(rows)
        self.assertEqual(metrics["total_images"], 3)
        self.assertEqual(metrics["evaluated_images"], 2)
        self.assertEqual(metrics["reviewed_images"], 1)
        self.assertEqual(metrics["accuracy_on_automatic_predictions"], 0.5)
        self.assertAlmostEqual(metrics["end_to_end_accuracy"], 1 / 3)
        self.assertEqual(metrics["per_class"]["stain_or_spot"]["recall"], 0.0)

    def test_yolo_crop_is_created(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            image_path = root / "garment.jpg"
            label_path = root / "garment.txt"
            output_path = root / "crop.jpg"
            from PIL import Image

            Image.new("RGB", (100, 100), "white").save(image_path)
            label_path.write_text("0 0.5 0.5 0.1 0.1\n", encoding="utf-8")
            result = create_yolo_crop(image_path, label_path, output_path)
            self.assertEqual(result, output_path)
            self.assertTrue(output_path.is_file())
            with Image.open(output_path) as crop:
                self.assertLess(crop.width, 100)
                self.assertLess(crop.height, 100)

    def test_yolo_backend_maps_highest_confidence_box(self):
        class Values:
            def __init__(self, values):
                self.values = values

            def tolist(self):
                return self.values

        class Boxes:
            conf = Values([0.42, 0.88])
            cls = Values([0, 1])

            def __len__(self):
                return 2

        class Result:
            boxes = Boxes()

        def predictor(*args, **kwargs):
            return [Result()]

        prediction = YoloBackend("unused.pt", predictor=predictor).predict(Path("image.jpg"))
        self.assertEqual(prediction.damage_type, "stain_or_spot")
        self.assertEqual(prediction.confidence, 0.88)

    def test_yolo_backend_routes_no_detection_to_review(self):
        class EmptyBoxes:
            def __len__(self):
                return 0

        class Result:
            boxes = EmptyBoxes()

        prediction = YoloBackend("unused.pt", predictor=lambda *args, **kwargs: [Result()]).predict(
            Path("image.jpg")
        )
        self.assertEqual(prediction.damage_type, "uncertain")
        self.assertEqual(prediction.confidence, 0.0)

    def test_prepare_yolo_dataset_excludes_entire_augmentation_group(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            holes = root / "holes"
            spots = root / "spots"
            for dataset in (holes, spots):
                for split in ("train", "valid"):
                    (dataset / split / "images").mkdir(parents=True)
                    (dataset / split / "labels").mkdir(parents=True)

            excluded = "same_original.rf.aaa.jpg"
            kept = "different_original.rf.bbb.jpg"
            (holes / "train" / "images" / excluded).write_bytes(b"image")
            (holes / "train" / "labels" / Path(excluded).with_suffix(".txt").name).write_text(
                "0 0.5 0.5 0.2 0.2\n", encoding="utf-8"
            )
            (spots / "valid" / "images" / kept).write_bytes(b"image")
            (spots / "valid" / "labels" / Path(kept).with_suffix(".txt").name).write_text(
                "0 0.5 0.5 0.2 0.2\n", encoding="utf-8"
            )

            counts = prepare_dataset(
                [SourceDataset(holes, 0), SourceDataset(spots, 1)],
                root / "prepared",
                {source_group(excluded)},
            )
            self.assertEqual(counts, {"train": 0, "val": 1, "excluded": 1})
            label = next((root / "prepared" / "val" / "labels").glob("*.txt"))
            self.assertTrue(label.read_text(encoding="utf-8").startswith("1 "))

    def test_segmentation_polygon_is_converted_to_box(self):
        converted = normalize_annotation(
            ["0", "0.2", "0.3", "0.6", "0.3", "0.6", "0.7", "0.2", "0.7"],
            class_id=1,
        )
        fields = converted.split()
        self.assertEqual(fields[0], "1")
        self.assertEqual(len(fields), 5)
        self.assertEqual([float(value) for value in fields[1:]], [0.4, 0.5, 0.4, 0.4])

    def test_review_metrics_separate_detection_from_automation(self):
        rows = [
            {
                "expected_label": "hole_or_tear",
                "predicted_label": "hole_or_tear",
                "confidence": 0.10,
            },
            {
                "expected_label": "stain_or_spot",
                "predicted_label": "stain_or_spot",
                "confidence": 0.80,
            },
            {
                "expected_label": "stain_or_spot",
                "predicted_label": "uncertain",
                "confidence": 0.0,
            },
        ]
        metrics = calculate_review_metrics(rows, review_threshold=0.70)
        self.assertEqual(metrics["review_free_images"], 1)
        self.assertEqual(metrics["human_review_images"], 2)
        self.assertAlmostEqual(metrics["automation_coverage"], 1 / 3)
        self.assertEqual(metrics["accuracy_on_review_free_predictions"], 1.0)


if __name__ == "__main__":
    unittest.main()
