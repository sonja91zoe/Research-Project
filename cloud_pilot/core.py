"""Image-only cloud feasibility probe; reuses Members 1 and 2."""
from io import BytesIO
from pathlib import Path
import tempfile
import threading
import time
import uuid
import warnings

from PIL import Image, UnidentifiedImageError
from src.agent.member1_adapter import run_member1
from src.common.schemas import CaseInput
from src.common.schemas import Member2Output
from src.damage_detection.damage import ClipBackend, skipped_damage_output
from src.damage_detection.runtime import (
    DamageBackend,
    build_member2_runtime,
    member2_runtime_metadata,
)

MAX_BYTES = 8 * 1024 * 1024


class CpuClipBackend(ClipBackend):
    def _get_classifier(self):
        if self._classifier is None:
            import torch
            from transformers import pipeline
            torch.set_num_threads(2)
            self._classifier = pipeline(
                'zero-shot-image-classification',
                model=self.MODEL_NAME,
                device=-1,
            )
        return self._classifier


class Runtime:
    def __init__(self, detector=None, product_classifier=None, *, backend: DamageBackend = 'yolo'):
        if detector is None:
            configured = build_member2_runtime(
                backend=backend, clip_backend=CpuClipBackend()
            )
            detector = configured.detector
            if product_classifier is None:
                product_classifier = configured.product_classifier
        self.detector = detector
        self.product_classifier = product_classifier
        self.lock = threading.Lock()


def validate_image(data):
    if not data or len(data) > MAX_BYTES:
        raise ValueError('Choose a JPEG or PNG image up to 8 MB.')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as image:
                if image.format not in {'JPEG', 'PNG'} or image.width * image.height > 20_000_000:
                    raise ValueError('Use a JPEG or PNG image up to 20 megapixels.')
                suffix = '.png' if image.format == 'PNG' else '.jpg'
                image.verify()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombWarning, Image.DecompressionBombError) as error:
        raise ValueError('The image could not be decoded safely.') from error
    return suffix


def analyze(data, claim, visible, runtime):
    suffix = validate_image(data)
    if not isinstance(claim, str) or not claim.strip() or len(claim) > 3000:
        raise ValueError('Enter an English claim of 1 to 3000 characters.')
    if type(visible) is not bool:
        raise ValueError('Specify whether the relevant area is visible.')
    if not runtime.lock.acquire(blocking=False):
        raise RuntimeError('Another image is being processed. Please try again shortly.')
    try:
        started = time.perf_counter()
        with tempfile.TemporaryDirectory(prefix='refund-pilot-') as folder:
            path = Path(folder) / ('image' + suffix)
            path.write_bytes(data)
            case = CaseInput(case_id=str(uuid.uuid4()), order_id='IMAGE-PILOT',
                             claim_text=claim.strip(), image_paths=[str(path)])
            member1, quality = run_member1(case, relevant_region_visible=visible)
            usable = member1.image_usable and member1.relevant_region_visible
            if usable:
                member2 = runtime.detector.detect(
                    case_id=case.case_id, image_path=path, evidence_quality='good'
                )
            else:
                member2 = skipped_damage_output(case.case_id, 'unusable')
            product_classification_completed = False
            if usable and runtime.product_classifier is not None:
                product = runtime.product_classifier.predict(path)
                product_classification_completed = True
                member2 = Member2Output.model_validate({
                    **member2.model_dump(),
                    'detected_product': product.product_type,
                    'product_confidence': product.confidence,
                    'rationale': f'{member2.rationale} {product.rationale}',
                })
            member2 = Member2Output.model_validate({
                **member2.model_dump(),
                'runtime_metadata': member2_runtime_metadata(
                    runtime.detector, runtime.product_classifier,
                    damage_inference_completed=usable,
                    product_classification_completed=product_classification_completed,
                ),
            })
            return {
                'scope': 'Image-quality and Member 2 visual inference pilot; no refund decision or payment.',
                'case_id': case.case_id,
                'claim_text': claim.strip(),
                'relevant_region_visible': visible,
                'elapsed_seconds': round(time.perf_counter() - started, 2),
                'member1': member1.model_dump(),
                'raw_image_quality': quality,
                'member2': member2.model_dump(),
            }
    finally:
        runtime.lock.release()
