"""Customer-owned workflow on top of the shared image pipeline."""
from app.refund_service import RefundService
from src.evidence.order import load_orders

DEMO_ACCOUNT = 'customer001'
DEMO_PASSWORD = 'Refund123!'

class PortalService(RefundService):
    def orders_for(self, account):
        if account != DEMO_ACCOUNT:
            return []
        from dataclasses import asdict
        return [asdict(o) for o in load_orders().values()]

    def _assess(self, record, payload):
        record = super()._assess(record, payload)
        if record['status'] == 'READY_TO_REFUND':
            record = self.confirm(record['case_id'])
        return record

    def create_for(self, account, payload):
        with self.lock:
            if payload.get('order_id') not in {o['order_id'] for o in self.orders_for(account)}:
                raise ValueError('The selected order does not belong to this account.')
            # Ownership is attached before any result is persisted.
            self._creating_account = account
            self._creating_product = next(o['product_name'] for o in self.orders_for(account) if o['order_id'] == payload['order_id'])
            try:
                return self.create(payload)
            finally:
                self._creating_account = None
                self._creating_product = None

    def _save(self, record):
        if not record.get('account_id') and getattr(self, '_creating_account', None):
            record['account_id'] = self._creating_account
            record['product_name'] = self._creating_product
        return super()._save(record)

    def owned(self, account, case_id):
        record = self.get(case_id)
        if record.get('account_id') != account:
            raise PermissionError('This application belongs to a different account.')
        return record

    def records(self, account=None):
        with self.lock:
            records = [self.get(row['case_id']) for row in self.list()]
            if account is not None:
                records = [r for r in records if r.get('account_id') == account]
            return records

    def staff_review(self, case_id, payload):
        with self.lock:
            record = self.review(case_id, payload)
            if record['status'] == 'READY_TO_REFUND':
                record = self.confirm(case_id)
            return record
