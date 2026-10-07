from cloud_pilot.presentation import evidence_summary

def test_negative_and_missing_are_distinct():
    result = {'member2': {'damage_type': 'stain_or_spot', 'claim_image_consistency': 0},
              'member2_verification': {'verdict': 'negative', 'reason_code': 'damage_type_mismatch'},
              'missing_evidence': ['detected_product', 'damage_location']}
    summary = evidence_summary(result)
    assert summary['verdict'] == 'Does not support the description'
    assert summary['damage'] == 'stain or spot'
    assert summary['location'] == 'Not identified'
    assert len(summary['missing']) == 2

def test_unknown_is_not_presented_as_support():
    assert evidence_summary({})['verdict'] == 'Not assessed'
    assert evidence_summary({'member2_verification': {'verdict': 'ambiguous'}})['verdict'] == 'Cannot confirm'

def test_product_prediction_and_order_match_are_visible():
    summary = evidence_summary({
        'member2': {
            'detected_product': 't-shirt',
            'product_confidence': 0.81,
            'damage_type': 'hole_or_tear',
        },
        'member3': {'image_order_match_status': 'MATCH'},
        'member2_verification': {},
        'missing_evidence': [],
    })
    assert summary['product'] == 't-shirt'
    assert summary['product_confidence'] == 0.81
    assert summary['order_match'] == 'Match'
