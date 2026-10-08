"""Build an isolated synthetic catalog from assistant visual review, not predictions."""
import copy
import hashlib
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Reviewed full photos in order H001-H035 then S001-S035. Not human ground truth.
HOLES = 'Trousers Trousers Shirt Trousers Trousers Jacket Shorts Jacket Jacket Trousers Trousers Trousers T-Shirt T-Shirt T-Shirt T-Shirt Jacket T-Shirt Jacket Trousers T-Shirt Trousers T-Shirt T-Shirt Jacket Trousers Trousers T-Shirt T-Shirt Trousers T-Shirt Trousers T-Shirt T-Shirt T-Shirt'.split()
SPOTS = 'T-Shirt T-Shirt T-Shirt Dress T-Shirt Jacket Jacket T-Shirt T-Shirt Trousers T-Shirt T-Shirt T-Shirt T-Shirt Trousers T-Shirt T-Shirt Trousers Trousers T-Shirt T-Shirt Unknown T-Shirt Trousers T-Shirt T-Shirt Unknown T-Shirt T-Shirt T-Shirt T-Shirt Trousers T-Shirt Jacket Sweater'.split()


def build():
    original = json.loads((ROOT / 'data/orders/orders.json').read_text())
    assert len(original) == len(HOLES + SPOTS) == 70
    orders = copy.deepcopy(original)
    for i, (order, category) in enumerate(zip(orders, HOLES + SPOTS), 1):
        assert order['order_id'] == f'ORD{i:03}'
        photo = ROOT / order['image_evidence']['image_path']
        order['product_category'] = category
        order['product_name'] = f'Simulated {category} — {order["image_evidence"]["source_image_id"]}'
        order['catalog_version'] = 'photo_matched_v1'
        order['photo_pairing'] = {
            'method': 'assistant_visual_review_of_full_photo',
            'human_verified': False,
            'category_status': 'uncertain' if category == 'Unknown' else 'provisional_visual_review',
            'original_category': original[i-1]['product_category'],
            'image_sha256': hashlib.sha256(photo.read_bytes()).hexdigest(),
            'identity_verified': False,
            'note': 'Category-level synthetic pairing only; not proof of purchase or exact item identity. No model predictions used to assign categories. Original simulated price, dates, delivery status and final-sale flags retained.',
        }
    return orders


if __name__ == '__main__':
    orders = build()
    destination = ROOT / 'data/orders/photo_matched_orders.json'
    destination.write_text(json.dumps(orders, ensure_ascii=False, indent=2) + '\n')
    cards = []
    for o in orders:
        image_path = '../../' + o['image_evidence']['image_path']
        cards.append(f'<article><img loading="lazy" src="{html.escape(image_path)}"><p>{o["order_id"]} / {o["image_evidence"]["source_image_id"]}<br>原类别：{o["photo_pairing"]["original_category"]}<br>照片核对类别：{o["product_category"]}</p></article>')
    (destination.parent / 'photo_matched_review.html').write_text('<!doctype html><meta charset="utf-8"><title>70 张照片与模拟订单</title><style>body{font:16px system-ui;margin:30px}main{display:grid;grid-template-columns:repeat(4,1fr);gap:20px}img{width:100%;height:250px;object-fit:contain}article{border:1px solid #ddd;padding:12px}</style><h1>70 张照片与模拟订单</h1><p>助手逐图初审，尚未由人工确认。未知类别不强行匹配。交易字段为模拟；不是模型准确率测试集。</p><main>'+''.join(cards)+'</main>')
    print(destination)
