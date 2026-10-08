import json
from scripts.build_photo_matched_orders import ROOT, build
from src.evidence.models import OrderRecord


def test_photo_catalog_preserves_transactions_and_mapping():
    original = json.loads((ROOT/'data/orders/orders.json').read_text())
    updated = build()
    assert len(updated) == 70
    assert len({o['image_evidence']['image_path'] for o in updated}) == 70
    for before, after in zip(original, updated):
        assert OrderRecord(**after).catalog_version == 'photo_matched_v1'
        for key in ('order_id', 'price', 'purchase_date', 'delivery_date', 'status', 'final_sale', 'image_evidence'):
            assert before[key] == after[key]
        assert after['photo_pairing']['identity_verified'] is False
        assert after['photo_pairing']['human_verified'] is False
    assert updated[0]['product_category'] == 'Trousers'
    assert updated[6]['product_category'] == 'Shorts'
    assert updated[56]['product_category'] == 'Unknown'
    assert updated[61]['product_category'] == 'Unknown'
