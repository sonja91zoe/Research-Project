from pathlib import Path
from io import BytesIO
from PIL import Image
import pytest
from cloud_pilot.core import Runtime, analyze
import src.damage_detection.runtime as runtime_config
from src.damage_detection.damage import DamageDetector, DamagePrediction, FixedBackend
from src.damage_detection.product import ProductTypeClassifier, ProductTypePrediction
from src.damage_detection.runtime import YOLO_WEIGHTS_ENV, resolve_yolo_weights
from src.damage_detection.yolo import YoloBackend


def png():
    b=BytesIO();Image.new('RGB',(30,30),'black').save(b,format='PNG');return b.getvalue()


def test_refund_studio_runtime_uses_canonical_models(monkeypatch):
    monkeypatch.delenv(YOLO_WEIGHTS_ENV, raising=False)
    monkeypatch.setattr(runtime_config, 'find_spec', lambda name: object())

    runtime = Runtime()

    assert isinstance(runtime.detector.backend, YoloBackend)
    assert runtime.detector.backend.weights == str(resolve_yolo_weights())
    assert isinstance(runtime.product_classifier, ProductTypeClassifier)


def test_refund_studio_invalid_weight_does_not_fall_back(monkeypatch, tmp_path):
    monkeypatch.setenv(YOLO_WEIGHTS_ENV, str(tmp_path / 'missing.pt'))

    with pytest.raises(FileNotFoundError, match='Member 2 YOLO weights were not found'):
        Runtime()


def test_cloud_assessment_reports_both_canonical_models(monkeypatch):
    root = Path(__file__).resolve().parents[1]
    monkeypatch.delenv(YOLO_WEIGHTS_ENV, raising=False)
    monkeypatch.setattr(runtime_config, 'find_spec', lambda name: object())
    monkeypatch.setattr(YoloBackend, 'predict', lambda self, path:
                        DamagePrediction('hole_or_tear', .9, 'controlled YOLO'))
    monkeypatch.setattr(ProductTypeClassifier, 'predict', lambda self, path:
                        ProductTypePrediction('jacket', .8, .2, 'controlled CLIP'))

    result = analyze(
        (root / 'data/member1/images/member1_jacket_001.jpg').read_bytes(),
        'The jacket has a hole.', True, Runtime(),
    )

    metadata = result['member2']['runtime_metadata']
    assert metadata['damage_backend'] == 'yolo'
    assert metadata['damage_weights_path'] == str(resolve_yolo_weights())
    assert len(metadata['damage_weights_sha256']) == 64
    assert metadata['product_classifier_backend'] == 'clip'
    assert metadata['product_model'] == ProductTypeClassifier.MODEL_NAME
    assert metadata['damage_inference_completed'] is True
    assert metadata['product_classification_completed'] is True
    assert 'clip_inference_completed' not in result
    assert 'model' not in result


def test_dark_image_reports_both_models_skipped():
    class Never:
        def predict(self,path):raise AssertionError('Damage inference should be skipped')
    result=analyze(png(),'The jacket has a hole.',True,Runtime(DamageDetector(Never())))
    metadata = result['member2']['runtime_metadata']
    assert metadata['damage_inference_completed'] is False
    assert metadata['product_classification_completed'] is False
    assert metadata['damage_backend'] is None
    assert 'clip_inference_completed' not in result
    assert 'model' not in result
    assert result['member1']['image_usable'] is False


def test_good_image_uses_detector_and_cleans_temporary_file():
    root=Path(__file__).resolve().parents[1]
    paths=[]
    class Backend:
        def predict(self,path):
            assert path.exists();paths.append(path)
            return DamagePrediction('stain_or_spot',.8,'controlled test')
    result=analyze((root/'data/member1/images/member1_jacket_001.jpg').read_bytes(),
                   'The jacket has a tear.',True,Runtime(DamageDetector(Backend())))
    metadata = result['member2']['runtime_metadata']
    assert metadata['damage_inference_completed'] is True
    assert metadata['product_classification_completed'] is False
    assert metadata['damage_backend'] is None
    assert metadata['product_classifier_backend'] is None
    assert paths and not paths[0].exists()


def test_good_image_adds_independent_product_prediction():
    root = Path(__file__).resolve().parents[1]

    class Backend:
        def predict(self, path):
            return DamagePrediction('hole_or_tear', .8, 'controlled damage')

    class ProductClassifier:
        def predict(self, path):
            return ProductTypePrediction('jacket', .82, .30, 'controlled product')

    runtime = Runtime(
        detector=DamageDetector(Backend()),
        product_classifier=ProductClassifier(),
    )
    result = analyze(
        (root / 'data/member1/images/member1_jacket_001.jpg').read_bytes(),
        'The jacket has a hole.',
        True,
        runtime,
    )

    assert result['member2']['detected_product'] == 'jacket'
    assert result['member2']['product_confidence'] == .82
    assert result['member2']['runtime_metadata']['product_classification_completed'] is True
    assert result['member2']['runtime_metadata']['product_classifier_backend'] is None


def test_invalid_image_and_busy_runtime():
    runtime=Runtime()
    with pytest.raises(ValueError):analyze(b'not an image','Claim',True,runtime)
    runtime.lock.acquire()
    try:
        with pytest.raises(RuntimeError,match='Another image'):analyze(png(),'Claim',True,runtime)
    finally:runtime.lock.release()
