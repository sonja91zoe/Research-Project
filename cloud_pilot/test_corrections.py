"""Controlled workflow tests, not model accuracy tests."""
import json
import pytest
from cloud_pilot.core import Runtime
from cloud_pilot.workflow import SessionRefundService
from cloud_pilot.test_workflow import payload


@pytest.fixture
def service(tmp_path):
    path = tmp_path / 'orders.json'
    path.write_text(json.dumps([dict(order_id=k, product_name='Shirt', product_category='Shirt', price=30,
        purchase_date='2026-08-01', delivery_date='2026-08-05', status='delivered') for k in ['ORD001','ORD002']]))
    return SessionRefundService(Runtime(detector=object()),
        pipeline=lambda *a, **k: {'decision': {'decision': 'HUMAN_REVIEW'}}, order_source=path)


def test_correction_preserves_history_and_revokes_approval(service):
    p = {**payload(), 'submitted_purchase_date':'2026-08-01'}
    r = service.create(p)
    first = r['assessments'][0]
    service.review(r['case_id'], dict(action='APPROVE', reviewer='Test', note='Test only'))
    r = service.amend(r['case_id'], {**p, 'order_id':'ORD002', 'claim_text':'The shirt has a stain.'})
    assert r['status'] == 'PENDING_REVIEW'
    assert r['order_id'] == 'ORD002'
    assert r['assessments'][0] == first
    assert r['assessments'][1]['inputs']['order_id'] == 'ORD002'
    assert r['assessments'][1]['date_check']['status'] == 'PURCHASE_DATE_MATCH'
    assert any(e['action']=='INPUT_CORRECTION' for e in r['events'])


@pytest.mark.parametrize('changes', [
    {'submitted_purchase_date':'bad'}, {'submitted_purchase_date':'2026-08-02'},
    {'request_date':'2026-08-04'}, {'order_id':'missing'}, {'claim_text':''}])
def test_invalid_correction_preserves_record(service, changes):
    p = {**payload(), 'submitted_purchase_date':'2026-08-01'}
    r = service.create(p)
    with pytest.raises(ValueError):
        service.amend(r['case_id'], {**p, **changes})
    assert service.get(r['case_id']) == r


def test_failed_model_preserves_record(service):
    p = {**payload(), 'submitted_purchase_date':'2026-08-01'}
    r = service.create(p)
    def fail(*a, **k):
        raise RuntimeError('Unavailable')
    service.pipeline = fail
    with pytest.raises(RuntimeError):
        service.amend(r['case_id'], p)
    assert service.get(r['case_id']) == r


def test_closed_case_cannot_be_changed(service):
    p = {**payload(), 'submitted_purchase_date':'2026-08-01'}
    r = service.create(p)
    service.review(r['case_id'], dict(action='APPROVE', reviewer='Test', note='Simulation'))
    service.confirm(r['case_id'])
    with pytest.raises(ValueError):
        service.amend(r['case_id'], p)


def test_invalid_create_leaves_no_record(service):
    with pytest.raises(ValueError):
        service.create({**payload(), 'submitted_purchase_date':'2026-08-02'})
    assert service.list() == []
