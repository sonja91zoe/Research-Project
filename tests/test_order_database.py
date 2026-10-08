import sqlite3
import pytest
from src.evidence.database import initialize, lookup, verify_dates, save_case
from src.evidence.order import load_orders, retrieve_order


@pytest.fixture
def db(tmp_path):
    path = tmp_path/'orders.db'
    initialize(path, [dict(order_id='TEST1', purchase_date='2026-09-01',
                           delivery_date='2026-09-05', product_name='Jacket',
                           product_category='jacket', price=49.0,
                           status='delivered')])
    return path


@pytest.mark.parametrize('purchase,requested,status', [
    ('2026-09-01','2026-09-15','PASS'),
    ('2026-09-02','2026-09-15','DATE_MISMATCH'),
    ('2026-09-01','2026-09-04','BEFORE_DELIVERY'),
    ('2026-09-01','2026-11-15','OUTSIDE_WINDOW'),
    ('bad','2026-09-15','INVALID_DATE'),
])
def test_date_results(db, purchase, requested, status):
    assert verify_dates(db,'TEST1',purchase,requested)['status'] == status


def test_unknown_and_injection(db):
    assert lookup(db,"' OR 1=1 --") is None
    assert verify_dates(db,'missing','2026-09-01','2026-09-15')['status']=='ORDER_NOT_FOUND'


def test_existing_data_preserved(db):
    with pytest.raises(ValueError, match='Conflicting'):
        initialize(db,[dict(order_id='TEST1',purchase_date='2026-08-01')])
    assert lookup(db,'test1')['purchase_date']=='2026-09-01'


def test_evidence_belongs_to_case(db):
    save_case(db,'CASE1','TEST1','a hole','new.jpg','2026-09-15')
    with pytest.raises(sqlite3.IntegrityError):
        save_case(db,'CASE2','missing','a hole','other.jpg','2026-09-15')


def test_pipeline_order_repository_can_read_sqlite(db):
    orders = load_orders(db)
    assert list(orders) == ['TEST1']
    assert retrieve_order('test1', db).purchase_date == '2026-09-01'
