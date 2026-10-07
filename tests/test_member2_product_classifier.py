from pathlib import Path

from src.agent.member2_adapter import run_member2_verification
from src.common.schemas import CaseInput, Member1Output
from src.damage_detection.damage import (
    DamageDetector,
    DamagePrediction,
    FixedBackend,
)
from src.damage_detection.product import ProductTypeClassifier
from src.evidence.order import retrieve_order
from src.evidence.verification import _image_order_match


def fake_classifier_for(top_prompt, top_score=0.70, second_score=0.08):
    def classify(_image, *, candidate_labels):
        results = []
        for prompt in candidate_labels:
            score = 0.01
            if prompt == top_prompt:
                score = top_score
            elif prompt == "a garment jacket with sleeves and a front opening":
                score = second_score
            results.append({"label": prompt, "score": score})
        return results

    return classify


def test_product_classifier_returns_independent_image_prediction(tmp_path):
    image = tmp_path / "evidence.jpg"
    image.write_bytes(b"test image bytes")
    classifier = ProductTypeClassifier(
        classifier=fake_classifier_for("a photo of a jacket")
    )

    prediction = classifier.predict(image)

    assert prediction.product_type == "jacket"
    assert prediction.confidence >= classifier.min_confidence
    assert prediction.margin >= classifier.min_margin


def test_product_classifier_rejects_ambiguous_scores(tmp_path):
    image = tmp_path / "evidence.jpg"
    image.write_bytes(b"test image bytes")

    def tied_classifier(_image, *, candidate_labels):
        return [{"label": label, "score": 1.0} for label in candidate_labels]

    prediction = ProductTypeClassifier(classifier=tied_classifier).predict(image)

    assert prediction.product_type is None
    assert prediction.margin == 0.0


def test_member2_adapter_does_not_copy_order_category_into_prediction(tmp_path):
    image = tmp_path / "evidence.jpg"
    image.write_bytes(b"test image bytes")
    case = CaseInput(
        case_id="PRODUCT-TEST",
        order_id="ORD001",
        claim_text="The jacket has a hole.",
        image_paths=[str(image)],
    )
    member1 = Member1Output(
        case_id=case.case_id,
        product="jacket",
        claimed_defect="tear_hole",
        image_quality=0.9,
        blur_score=0.1,
        lighting_score=0.9,
        relevant_region_visible=True,
        image_usable=True,
    )
    detector = DamageDetector(
        FixedBackend(DamagePrediction("hole_or_tear", 0.9, "damage only"))
    )
    product_classifier = ProductTypeClassifier(
        classifier=fake_classifier_for("a photo of a dress")
    )

    result = run_member2_verification(
        case,
        member1,
        detector=detector,
        product_classifier=product_classifier,
    )

    assert result.member2.detected_product == "dress"
    assert result.member2.detected_product != member1.product


def test_member3_uses_confidence_for_match_mismatch_and_unknown():
    order = retrieve_order("ORD001")
    assert order is not None

    assert _image_order_match("jacket", order, 0.80)[1] == "MATCH"
    assert _image_order_match("dress", order, 0.80)[1] == "MISMATCH"
    assert _image_order_match("jacket", order, 0.10)[1] == "NOT_AVAILABLE"
    assert _image_order_match("", order, None)[1] == "NOT_AVAILABLE"


def test_member3_normalizes_common_product_synonyms():
    order = retrieve_order("ORD003")
    assert order is not None
    assert _image_order_match("tee", order, 0.80)[1] == "MATCH"
