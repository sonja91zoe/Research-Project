from src.evidence.order import load_orders
from src.evidence.verification import verify_case, policy_for_order

CATALOG = 'data/orders/member4_portal_orders.json'


def test_single_order_metadata_and_reference_image():
    from pathlib import Path
    orders = load_orders(CATALOG)
    assert list(orders) == ['ADI001']
    order = orders['ADI001']
    assert order.product_category == 'Hoodie'
    assert order.photo_pairing['size'] == 'M'
    assert order.price == 100
    assert Path(order.photo_pairing['reference_image_path']).is_file()
    assert policy_for_order(order, 'hoodie hole').refund_window_days == 30


def test_new_order_category_and_delivery_window():
    case = dict(case_id='test', order_id='ADI001', claim_text='hoodie hole',
                detected_product='hoodie', product_confidence=.957,
                image_present=True, image_usable=True, damage_detected=True,
                damage_type='hole_or_tear', claim_image_consistency=.9,
                request_date='2026-10-11')
    result = verify_case(case, order_source=CATALOG)
    assert result.image_order_match_status == 'MATCH'
    assert result.policy_eligible
    for invalid_date in ['2026-10-04', '2026-11-05']:
        case['request_date'] = invalid_date
        assert not verify_case(case, order_source=CATALOG).policy_eligible
