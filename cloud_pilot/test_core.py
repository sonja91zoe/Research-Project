from pathlib import Path
from io import BytesIO
from PIL import Image
import pytest
from cloud_pilot.core import Runtime, analyze
from src.damage_detection.damage import DamageDetector, DamagePrediction, FixedBackend
from src.damage_detection.product import ProductTypePrediction


def png():
    b=BytesIO();Image.new('RGB',(30,30),'black').save(b,format='PNG');return b.getvalue()


def test_dark_image_does_not_claim_clip_success():
    class Never:
        def predict(self,path):raise AssertionError('CLIP should be skipped')
    result=analyze(png(),'The jacket has a hole.',True,Runtime(DamageDetector(Never())))
    assert result['clip_inference_completed'] is False
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
    assert result['clip_inference_completed'] is True
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


def test_invalid_image_and_busy_runtime():
    runtime=Runtime()
    with pytest.raises(ValueError):analyze(b'not an image','Claim',True,runtime)
    runtime.lock.acquire()
    try:
        with pytest.raises(RuntimeError,match='Another image'):analyze(png(),'Claim',True,runtime)
    finally:runtime.lock.release()
