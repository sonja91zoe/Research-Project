import pytest
from cloud_pilot.core import Runtime
from cloud_pilot.persistent_workflow import LocalSqliteRefundService
from cloud_pilot.test_workflow import payload
from src.evidence.database import connect


def test_catalog_switch_keeps_historical_orders(tmp_path):
    import json
    from src.evidence.order import load_orders
    database = tmp_path / 'cases.db'
    old = dict(order_id='ZEN001', product_name='Historical sample',
               product_category='Shirt', price=49.0,
               purchase_date='2026-09-01', delivery_date='2026-09-05',
               status='delivered')
    source = tmp_path / 'old.json'
    source.write_text(json.dumps([old]))
    LocalSqliteRefundService(Runtime(detector=object()), database, order_source=source)
    service = LocalSqliteRefundService(Runtime(detector=object()), database)
    orders = load_orders(service.order_source)
    assert 'ZEN001' in orders
    assert 'ORD001' in orders
    assert orders['ZEN001'].product_name == 'Historical sample'


def test_restart_corrections_review_and_refund(tmp_path):
    path = tmp_path/'cases.db'
    def service():
        return LocalSqliteRefundService(Runtime(detector=object()), path,
            pipeline=lambda *a, **k: {'decision': {'decision': 'HUMAN_REVIEW'}})
    a = service()
    r = a.create(payload())
    key = r['case_id']
    assert service().get(key) == r
    import base64
    assert service().image(key, 0)[0] == base64.b64decode(payload()['image_base64'])
    a.review(key, dict(action='REQUEST_MORE_EVIDENCE', reviewer='Test', note='Test'))
    r = service().evidence(key, payload())
    assert len(r['assessments']) == 2
    r = service().amend(key, {**payload(), 'claim_text':'The jacket has a hole.'})
    assert len(r['assessments']) == 3
    service().review(key, dict(action='APPROVE', reviewer='Test', note='Simulation only'))
    r = service().confirm(key)
    assert service().get(key) == r
    assert service().confirm(key) == r
    assert r['status'] == 'SIMULATED_REFUNDED'
    assert service().image(key, 2)[0] == base64.b64decode(payload()['image_base64'])
    with connect(path) as db:
        assert db.execute('SELECT count(*) FROM refund_cases').fetchone()[0] == 1


def test_stale_write_rejected(tmp_path):
    a = LocalSqliteRefundService(Runtime(detector=object()), tmp_path/'cases.db',
        pipeline=lambda *a, **k: {'decision': {'decision': 'HUMAN_REVIEW'}})
    r = a.create(payload())
    a.review(r['case_id'], dict(action='REJECT', reviewer='Test', note='Test'))
    with pytest.raises(ValueError, match='another session'):
        a._save(r)
    assert a.get(r['case_id'])['status'] == 'REJECTED'
