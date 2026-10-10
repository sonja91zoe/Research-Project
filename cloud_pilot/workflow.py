"""Session-owned records; only the locked Member 2 runtime is shared."""
from copy import deepcopy
from pathlib import Path
import tempfile
from datetime import date
from src.evidence.order import retrieve_order, DEFAULT_ORDER_DB

from app.refund_service import RefundService, STATES, now
from cloud_pilot.core import validate_image
from src.agent.pipeline import run_pipeline
from src.common.schemas import CaseInput


class SessionRefundService(RefundService):
    def __init__(self, runtime, pipeline=run_pipeline, order_source=None):
        super().__init__(pipeline=pipeline)
        self.runtime = runtime
        self.order_source = order_source
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

    def amend(self, case_id, payload):
        """Reassess corrected inputs atomically; preserve previous assessments."""
        record = self.get(case_id)
        if record['status'] in {'SIMULATED_REFUNDED', 'REJECTED'}:
            raise ValueError('This application is closed; start a new application.')
        before = {k: record.get(k) for k in ('order_id', 'claim_text', 'request_date', 'submitted_purchase_date')}
        for field, limit in [('order_id', 80), ('claim_text', 3000)]:
            value = payload.get(field)
            if not isinstance(value, str) or not value.strip() or len(value) > limit:
                raise ValueError(f'{field} is required (maximum {limit} characters).')
            record[field] = value.strip().upper() if field == 'order_id' else value.strip()
        date.fromisoformat(payload['request_date'])
        record['request_date'] = payload['request_date']
        record.pop('submitted_purchase_date', None)
        record['events'].append({'at': now(), 'action': 'INPUT_CORRECTION',
                                 'status': record['status'], 'previous_inputs': before})
        return self._assess(record, payload)

    def _save_assessment(self, record, data):
        return self._save(record)

    def _assess(self, record, payload):
        submitted = payload.get('submitted_purchase_date', record.get('submitted_purchase_date'))
        date_check = {'status': 'NOT_PROVIDED'}
        if submitted is not None:
            try:
                purchase = date.fromisoformat(submitted)
            except (ValueError, TypeError):
                raise ValueError('Enter a valid purchase date in YYYY-MM-DD format.')
            order = retrieve_order(record['order_id'], self.order_source or DEFAULT_ORDER_DB)
            if order is None:
                raise ValueError('Order not found; select a valid order.')
            if purchase != date.fromisoformat(order.purchase_date):
                raise ValueError('Purchase date does not match the selected order. Correct the date or order.')
            requested = date.fromisoformat(record['request_date'])
            if requested < purchase or (order.delivery_date and requested < date.fromisoformat(order.delivery_date)):
                raise ValueError('Request date is before purchase or delivery. Correct the date.')
            date_check = {'status': 'PURCHASE_DATE_MATCH', 'submitted_purchase_date': submitted,
                          'stored_purchase_date': order.purchase_date,
                          'note': 'Stored-record comparison only; refund eligibility is checked separately.'}
            record['submitted_purchase_date'] = submitted
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
                    confidence_method='rule', detector=self.runtime.detector,
                    product_classifier=self.runtime.product_classifier,
                    order_source=self.order_source)
                status = STATES[result['decision']['decision']]
        finally:
            self.runtime.lock.release()
        record['assessments'].append({'at': now(), 'relevant_region_visible': visible, 'result': result,
            'date_check': date_check,
            'inputs': {k: record.get(k) for k in ('order_id', 'claim_text', 'request_date', 'submitted_purchase_date')}})
        record['status'] = status
        record['events'].append({'at': now(), 'action': 'ASSESSMENT', 'status': status})
        return self._save_assessment(record, data)
