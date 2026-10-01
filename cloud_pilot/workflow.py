"""Session-owned records; only the locked CLIP runtime is shared."""
from copy import deepcopy
from pathlib import Path
import tempfile

from app.refund_service import RefundService, STATES, now
from cloud_pilot.core import validate_image
from src.agent.pipeline import run_pipeline
from src.common.schemas import CaseInput


class SessionRefundService(RefundService):
    def __init__(self, runtime, pipeline=run_pipeline):
        super().__init__(pipeline=pipeline)
        self.runtime = runtime
        self.records = {}

    def get(self, case_id):
        if case_id not in self.records:
            raise ValueError('Application not found in this browser session.')
        return deepcopy(self.records[case_id])

    def list(self):
        return sorted([{'case_id': r['case_id'], 'order_id': r['order_id'],
                        'status': r['status'], 'updated_at': r['updated_at']}
                       for r in self.records.values()], key=lambda r: r['updated_at'], reverse=True)

    def _save(self, record):
        record['updated_at'] = now()
        self.records[record['case_id']] = deepcopy(record)
        return deepcopy(record)

    def create(self, payload):
        if len(self.records) >= 10:
            raise ValueError('This demo allows 10 applications per session. Download your records before clearing the session.')
        return super().create({**payload, 'confidence_method': 'rule'})

    def _assess(self, record, payload):
        if len(record['assessments']) >= 10:
            raise ValueError('This demo allows 10 image assessments per application.')
        visible = payload.get('relevant_region_visible')
        if type(visible) is not bool:
            raise ValueError('Specify whether the claimed area is visible.')
        data, _ = self._image(payload)
        suffix = validate_image(data)
        if not self.runtime.lock.acquire(blocking=False):
            raise RuntimeError('Another photo is being analyzed. Please try again shortly.')
        try:
            with tempfile.TemporaryDirectory(prefix='refund-workflow-') as folder:
                path = Path(folder) / ('photo' + suffix)
                path.write_bytes(data)
                result = self.pipeline(
                    CaseInput(case_id=record['case_id'], order_id=record['order_id'],
                              claim_text=record['claim_text'], image_paths=[str(path)]),
                    request_date=record['request_date'], relevant_region_visible=visible,
                    confidence_method='rule', detector=self.runtime.detector)
                status = STATES[result['decision']['decision']]
        finally:
            self.runtime.lock.release()
        record['assessments'].append({'at': now(), 'relevant_region_visible': visible, 'result': result})
        record['status'] = status
        record['events'].append({'at': now(), 'action': 'ASSESSMENT', 'status': status})
        return self._save(record)
