import pytest
from scripts.build_member3_dataset_manifest import build_manifest


def test_manifest_does_not_promote_mock_category_to_ground_truth(tmp_path):
    (tmp_path / 'photo.jpg').write_bytes(b'test image bytes')
    order = {'order_id': 'ORD1', 'product_category': 'Jacket',
             'data_type': 'synthetic_order',
             'image_evidence': {'image_path': 'photo.jpg'}}
    case = build_manifest([order], tmp_path)['cases'][0]
    assert case['verified_product_category'] is None
    assert case['pairing_verified'] is False
    assert len(case['image_sha256']) == 64
    assert order['product_category'] == 'Jacket'
    with pytest.raises(ValueError, match='Duplicate'):
        build_manifest([order, order], tmp_path)


def test_manifest_rejects_missing_image(tmp_path):
    with pytest.raises(FileNotFoundError):
        build_manifest([{'order_id': 'ORD1', 'product_category': 'Jacket',
                         'image_evidence': {'image_path': 'missing.jpg'}}], tmp_path)
