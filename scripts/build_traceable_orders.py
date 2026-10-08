"""Build a separate, source-labelled 70-order demo and SQLite database."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path
from src.evidence.database import initialize, verify_dates

TYPES = {'T-shirt': 't-shirt', 'Shirt': 'shirt', 'Dress': 'dress',
         'Skirt': 'skirt', 'Jacket': 'jacket', 'Trousers': 'trousers',
         'Sweater': 'sweater', 'Hoodie': 'hoodie'}


def build(source, output, count=70):
    output.mkdir(parents=True, exist_ok=True)
    records = []
    seen_images = set()
    for label in sorted(source.rglob('labels_*.json')):
        raw = json.loads(label.read_text())
        category = TYPES.get(raw.get('type'))
        image = label.with_name(label.name.replace('labels_', 'front_')).with_suffix('.jpg')
        if not category or not image.is_file():
            continue
        digest = hashlib.sha256(image.read_bytes()).hexdigest()
        if digest in seen_images:
            continue
        seen_images.add(digest)
        sample = label.stem.removeprefix('labels_')
        target = output / 'images' / image.name
        target.parent.mkdir(exist_ok=True)
        shutil.copy2(image, target)
        records.append(dict(
            order_id=f'ZEN{i:03d}' if (i := len(records)+1) else '',
            product_name=category.title(), product_category=category,
            price=49.0, purchase_date='2026-09-01', delivery_date='2026-09-05',
            status='delivered', final_sale=False, retailer='H&M Australia',
            data_type='synthetic_order',
            image_evidence={'image_path': str(target), 'source_image_id': sample,
                'source_dataset': 'Zenodo 8386668', 'license': 'CC BY 4.0',
                'source_url': 'https://zenodo.org/records/8386668',
                'category_source': 'dataset expert annotation',
                'source_annotation': str(label.relative_to(source)),
                'image_sha256': digest,
                'original_annotation': raw, 'is_model_ground_truth': False},
        ))
        if len(records) == count:
            break
    if len(records) != count:
        raise ValueError(f'Only {len(records)} eligible samples found')
    (output / 'orders.json').write_text(json.dumps(records, indent=2)+'\n')
    initialize(output / 'orders.db', records)
    results = [verify_dates(output/'orders.db', r['order_id'], r['purchase_date'],
                            '2026-09-15') for r in records]
    (output/'date_results.json').write_text(json.dumps(results, indent=2)+'\n')
    print(f'Created {len(records)} annotated synthetic orders; date checks: '
          f'{sum(r["status"] == "PASS" for r in results)} PASS')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=Path('artifacts/traceable_orders'))
    args = parser.parse_args()
    build(args.source, args.output)
