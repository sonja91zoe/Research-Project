from dataclasses import replace
from src.evidence.order import retrieve_order
from src.evidence.verification import _image_order_match, _policy_eligibility
from src.evidence.rag import retrieve_best_policy


def test_unknown_is_not_mismatch_or_match():
    order = replace(retrieve_order('ORD001'), product_name='Unverified', product_category='Unknown')
    assert _image_order_match('jacket', order, 0.9) == (0.5, 'NOT_AVAILABLE')
    assert _image_order_match('Unknown', retrieve_order('ORD001'), 0.9) == (0.5, 'NOT_AVAILABLE')


def test_unknown_order_cannot_bypass_review():
    order = replace(retrieve_order('ORD001'), product_category='Unknown', status='delivered', final_sale=False)
    policy = retrieve_best_policy('hole', retailer=order.retailer)
    eligible, reason = _policy_eligibility({'request_date':order.delivery_date},order,policy,'NOT_AVAILABLE')
    assert not eligible
    assert 'unverified' in reason
