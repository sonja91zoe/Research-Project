"""Real local workflow probe with explicitly synthetic orders; no training."""
import base64
import json
import time
import sys
import hashlib
from pathlib import Path
from copy import deepcopy
from cloud_pilot.core import Runtime
from cloud_pilot.workflow import SessionRefundService
from cloud_pilot.presentation import evidence_summary


def main():
    root = Path(__file__).resolve().parents[1]
    out = root / 'artifacts' / ('external_workflow_' + time.strftime('%Y%m%d_%H%M%S'))
    out.mkdir()
    human = json.loads((root / 'data/external_test_pending/external_photo_human_review.json').read_text())['cases']
    categories = {'t shirt': 'T-Shirt', 't-shirt': 'T-Shirt', 'tshirt': 'T-Shirt', '牛仔褲': 'Jeans', '上衣 襯衫': 'Shirt', '襯衫': 'Shirt', '未知': 'Unknown'}
    orders = [dict(order_id=f'EXT{i:03}', product_name='SIMULATED '+categories[r['category']],
                   product_category=categories[r['category']], price=35.0,
                   purchase_date='2026-10-01', delivery_date='2026-10-03', status='delivered',
                   data_type='synthetic_order', retailer='H&M Australia') for i,r in enumerate(human,1)]
    order_path = out / 'synthetic_orders.json'
    order_path.write_text(json.dumps(orders, indent=2))
    runtime = Runtime()
    results = []
    for row, order in zip(human, orders):
        service = SessionRefundService(runtime, order_source=order_path)
        # Human labels construct a simulated customer claim only, never model output.
        damage = {'hole_or_tear':'a hole', 'stain_or_spot':'a stain', 'discoloration':'discoloration'}[row['defect']]
        image_path = root/'data/external_test_pending'/row['file']
        candidate = image_path.parent/'upload_copies'/Path(row['file']).with_suffix('.jpg').name
        if '--upload-copies' in sys.argv and candidate.is_file():
            image_path = candidate
        payload = dict(order_id=order['order_id'], request_date='2026-10-08',
                       claim_text=f"The {order['product_category']} has {damage}.",
                       relevant_region_visible=True,
                       image_base64=base64.b64encode(image_path.read_bytes()).decode())
        item = dict(file=row['file'], order_id=order['order_id'], synthetic_claim=payload['claim_text'])
        item.update(input_path=str(image_path.relative_to(root)), input_sha256=hashlib.sha256(image_path.read_bytes()).hexdigest(), original_sha256=row['sha256'])
        try:
            record = service.create(payload)
            first = deepcopy(record['assessments'][0])
            item['initial_status'] = record['status']
            item['summary'] = evidence_summary(first['result'])
            # Exercise supplementation without claiming it is new evidence.
            if record['status'] == 'PENDING_REVIEW':
                record = service.review(record['case_id'], dict(action='REQUEST_MORE_EVIDENCE', reviewer='Automated workflow test', note='Simulation only: request re-upload to exercise the state transition.'))
            if record['status'] == 'NEEDS_EVIDENCE':
                record = service.evidence(record['case_id'], payload)
                item['same_photo_resubmission_tested'] = True
            assert record['assessments'][0] == first
            if record['status'] == 'PENDING_REVIEW':
                record = service.review(record['case_id'], dict(action='APPROVE', reviewer='Automated workflow test', note='Simulated approval to test payment-free workflow, not evidence approval by a person.'))
            if record['status'] == 'READY_TO_REFUND':
                record = service.confirm(record['case_id'])
                assert service.confirm(record['case_id']) == record
            item['final_status'] = record['status']
            item['record'] = record
            # JSON intentionally converts policy tuples into arrays.
            exported = json.loads(json.dumps(record))
            assert exported['case_id'] == record['case_id']
            assert exported['status'] == record['status']
            assert json.dumps(exported, sort_keys=True) == json.dumps(record, sort_keys=True)
            item['json_export_verified'] = True
        except Exception as exc:
            item['error'] = f'{type(exc).__name__}: {exc}'
        results.append(item)
        print(json.dumps({k:v for k,v in item.items() if k not in ('record','summary')},ensure_ascii=False), flush=True)
        (out/'results.json').write_text(json.dumps({'scope':'Real inference; synthetic orders, claims and review actions; no real payment. Same photo resubmitted, not new evidence. No UI click validation.', 'results':results},ensure_ascii=False,indent=2))
    print('OUTPUT',out,flush=True)


if __name__ == '__main__':
    main()
