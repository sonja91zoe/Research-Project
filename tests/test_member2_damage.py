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


if __name__ == "__main__":
    unittest.main()
