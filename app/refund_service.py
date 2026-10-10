"""Persistent local demo workflow. No payment provider or reviewer authentication."""
import base64
from copy import deepcopy
from datetime import date, datetime, timezone
from io import BytesIO
import json
from pathlib import Path
import threading
import uuid
import warnings

from PIL import Image, UnidentifiedImageError
from src.agent.pipeline import run_pipeline
from src.common.schemas import CaseInput

ROOT = Path(__file__).resolve().parents[1]
MAX_IMAGE_BYTES = 8 * 1024 * 1024
STATES = {"AUTO_REFUND": "READY_TO_REFUND", "REQUEST_MORE_EVIDENCE": "NEEDS_EVIDENCE", "HUMAN_REVIEW": "PENDING_REVIEW"}


def now():
    return datetime.now(timezone.utc).isoformat()


class RefundService:
    def __init__(self, directory=None, pipeline=None):
        self.directory = Path(directory or ROOT / '.local_refund')
        self.pipeline = pipeline or run_pipeline
        self.lock = threading.RLock()
        self.detector = None
        self.product_classifier = None
        self.model = None

    def _path(self, case_id):
        if not isinstance(case_id, str) or str(uuid.UUID(case_id)) != case_id:
            raise ValueError('Invalid application ID.')
        return self.directory / case_id / 'record.json'

    def get(self, case_id):
        with self.lock:
            return json.loads(self._path(case_id).read_text(encoding='utf-8'))

    def list(self):
        with self.lock:
            rows = [json.loads(p.read_text()) for p in self.directory.glob('*/record.json')]
            return sorted([{'case_id': r['case_id'], 'order_id': r['order_id'], 'status': r['status'], 'updated_at': r['updated_at']} for r in rows], key=lambda r: r['updated_at'], reverse=True)

    def _save(self, record):
        path = self._path(record['case_id'])
        path.parent.mkdir(parents=True, exist_ok=True)
        record['updated_at'] = now()
        temp = path.with_suffix('.tmp')
        temp.write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        temp.replace(path)
        return deepcopy(record)

    def _image(self, payload):
        value = payload.get('image_base64')
        if not isinstance(value, str) or len(value) > (MAX_IMAGE_BYTES * 4 // 3 + 4):
            raise ValueError('Choose one JPEG or PNG image, at most 8 MB.')
        try:
            data = base64.b64decode(value, validate=True)
            if not data or len(data) > MAX_IMAGE_BYTES:
                raise ValueError('Image must be between 1 byte and 8 MB.')
            with warnings.catch_warnings():
                warnings.simplefilter('error', Image.DecompressionBombWarning)
                with Image.open(BytesIO(data)) as im:
                    if im.format not in {'PNG', 'JPEG'} or im.width * im.height > 20_000_000:
                        raise ValueError('Use a JPEG or PNG image of at most 20 megapixels.')
                    extension = '.png' if im.format == 'PNG' else '.jpg'
                    im.verify()
            return data, extension
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
            raise ValueError('The uploaded image is invalid or too large.') from error

    def _assess(self, record, payload):
        visible = payload.get('relevant_region_visible')
        if type(visible) is not bool:
            raise ValueError('Specify whether the claimed area is visible.')
        data, extension = self._image(payload)
        folder = self._path(record['case_id']).parent
        folder.mkdir(parents=True, exist_ok=True)
        filename = uuid.uuid4().hex + extension
        image_path = folder / filename
        image_path.write_bytes(data)
        try:
            kwargs = {}
            if self.pipeline is run_pipeline:
                from src.damage_detection.runtime import build_member2_runtime
                if self.detector is None:
                    configured = build_member2_runtime()
                    self.detector = configured.detector
                    self.product_classifier = configured.product_classifier
                kwargs['detector'] = self.detector
                kwargs['product_classifier'] = self.product_classifier
                if record['confidence_method'] == 'ml':
                    import joblib
                    if self.model is None:
                        self.model = joblib.load(ROOT / 'models/student4_evidence_confidence_v1.joblib')
                    kwargs['model'] = self.model
            result = self.pipeline(CaseInput(case_id=record['case_id'], order_id=record['order_id'], claim_text=record['claim_text'], image_paths=[str(image_path.resolve())]), request_date=record['request_date'], relevant_region_visible=visible, confidence_method=record['confidence_method'], **kwargs)
            status = STATES[result['decision']['decision']]
        except Exception:
            image_path.unlink(missing_ok=True)
            raise
        record['assessments'].append({'at': now(), 'image': filename, 'relevant_region_visible': visible, 'result': result})
        record['status'] = status
        record['events'].append({'at': now(), 'action': 'ASSESSMENT', 'status': status})
        return self._save(record)

    def create(self, payload):
        with self.lock:
            for field, limit in [('order_id', 80), ('claim_text', 3000)]:
                if not isinstance(payload.get(field), str) or not payload[field].strip() or len(payload[field]) > limit:
                    raise ValueError(f'{field} is required and must be at most {limit} characters.')
            request_date = payload.get('request_date')
            if not isinstance(request_date, str):
                raise ValueError('Request date is required.')
            date.fromisoformat(request_date)
            method = payload.get('confidence_method', 'ml')
            if method not in {'rule', 'ml'}:
                raise ValueError('Unsupported confidence method.')
            record = {'case_id': str(uuid.uuid4()), 'order_id': payload['order_id'].strip().upper(), 'claim_text': payload['claim_text'].strip(), 'request_date': request_date, 'confidence_method': method, 'created_at': now(), 'status': 'PROCESSING', 'assessments': [], 'events': []}
            return self._assess(record, payload)

    def evidence(self, case_id, payload):
        with self.lock:
            record = self.get(case_id)
            if record['status'] != 'NEEDS_EVIDENCE':
                raise ValueError('This application is not awaiting evidence.')
            return self._assess(record, payload)

    def review(self, case_id, payload):
        with self.lock:
            record = self.get(case_id)
            if record['status'] != 'PENDING_REVIEW':
                raise ValueError('This application is not awaiting review.')
            states = {'APPROVE': 'READY_TO_REFUND', 'REJECT': 'REJECTED', 'REQUEST_MORE_EVIDENCE': 'NEEDS_EVIDENCE'}
            action = payload.get('action')
            if action not in states:
                raise ValueError('Unsupported review action.')
            for field in ('reviewer', 'note'):
                if not isinstance(payload.get(field), str) or not payload[field].strip() or len(payload[field]) > 2000:
                    raise ValueError('Reviewer name and review note are required (maximum 2000 characters).')
            record['status'] = states[action]
            record['events'].append({'at': now(), 'action': 'HUMAN_'+action, 'reviewer': payload['reviewer'].strip(), 'note': payload['note'].strip(), 'status': record['status']})
            return self._save(record)

    def confirm(self, case_id):
        with self.lock:
            record = self.get(case_id)
            if record['status'] == 'SIMULATED_REFUNDED':
                return record
            if record['status'] != 'READY_TO_REFUND':
                raise ValueError('A refund recommendation or reviewer approval is required.')
            record['status'] = 'SIMULATED_REFUNDED'
            record['events'].append({'at': now(), 'action': 'SIMULATED_REFUND', 'status': record['status'], 'note': 'Demo only. No money transferred.'})
            return self._save(record)

    def image(self, case_id, revision):
        record = self.get(case_id)
        if revision < 0 or revision >= len(record['assessments']):
            raise ValueError('Invalid evidence revision.')
        path = self._path(case_id).parent / record['assessments'][revision]['image']
        return path.read_bytes(), 'image/png' if path.suffix == '.png' else 'image/jpeg'
