"""Build an audit manifest, not model inputs or genuine transaction records."""
import hashlib
import json
from pathlib import Path


def build_manifest(orders, root):
    root = Path(root).resolve()
    cases = []
    seen = set()
    for order in orders:
        key = order['order_id']
        if key in seen:
            raise ValueError(f'Duplicate order ID: {key}')
        seen.add(key)
        evidence = order.get('image_evidence') or {}
        relative = evidence.get('image_path')
        if not relative:
            raise ValueError(f'Missing image mapping: {key}')
        image = (root / relative).resolve()
        if not image.is_relative_to(root):
            raise ValueError('Image must be inside project')
        digest = hashlib.sha256(image.read_bytes()).hexdigest()
        cases.append({
            'order_id': key,
            'source_image_id': evidence.get('source_image_id'),
            'source_dataset': evidence.get('source_dataset'),
            'image_path': relative,
            'image_sha256': digest,
            'order_data_type': order.get('data_type', 'unspecified'),
            'historical_product_category': order['product_category'],
            'verified_product_category': None,
            'category_review_status': 'PENDING_HUMAN_REVIEW',
            'pairing_verified': False,
            'training_overlap_status': 'NOT_AUDITED',
        })
    return {
        'purpose': 'Member 2 / Member 3 integration; not an independent model benchmark',
        'notes': [
            'Historical order descriptions are synthetic, not visual ground truth.',
            'Pending category review does not assert a mismatch or a correct pairing.',
            'Review labels are evaluation metadata, never model predictions.',
            'No original orders or images were changed by this build.',
        ],
        'count': len(cases), 'cases': cases,
    }


def main():
    root = Path(__file__).resolve().parents[1]
    orders = json.loads((root / 'data/orders/orders.json').read_text())
    output = root / 'data/evaluation/member3_primary_manifest.json'
    if output.exists():
        raise FileExistsError('Manifest exists; preserve human review edits instead of overwriting')
    manifest = build_manifest(orders, root)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'Created {len(manifest["cases"])} traceable review entries: {output.name}')


if __name__ == '__main__':
    main()
