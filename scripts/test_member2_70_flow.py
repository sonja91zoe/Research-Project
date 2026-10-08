"""Member 2 ORD catalog integration test, distinct from Zenodo evaluation."""
import base64
import hashlib
import html
import json
import shutil
import time
import random
import sys
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from cloud_pilot.core import Runtime
from cloud_pilot.workflow import SessionRefundService


def main():
    root = Path(__file__).resolve().parents[1]
    source = root/('data/orders/photo_matched_orders.json' if '--photo-matched' in sys.argv else 'data/orders/orders.json')
    orders = json.loads(source.read_text())
    assert len(orders) == 70
    assert {o['order_id'] for o in orders} == {f'ORD{i:03}' for i in range(1,71)}
    out = root/'artifacts'/('member2_70_flow_'+datetime.now(ZoneInfo('Australia/Sydney')).strftime('%Y%m%d_%H%M%S'))
    (out/'images').mkdir(parents=True)
    normal_scenario = '--delivered-scenario' in sys.argv
    if normal_scenario:
        # Separate counterfactual fixture, never alter original order history.
        for order in orders:
            order['status'] = 'delivered'
            order['final_sale'] = False
    (out/'orders_snapshot.json').write_text(json.dumps(orders,ensure_ascii=False,indent=2))
    runtime=Runtime()
    rng=random.Random(32933)
    overdue=set()
    rows=[]
    started=time.monotonic()
    for o in orders:
        evidence=o['image_evidence']
        assert evidence['source_dataset'] in ('Garment_condition_holes','Garment_condition_spots')
        p=root/evidence['image_path']
        defect='a hole' if evidence['source_dataset']=='Garment_condition_holes' else 'a stain'
        purchase=date.fromisoformat(o['purchase_date'])
        delivery=date.fromisoformat(o['delivery_date'])
        # Overdue samples exceed 30 days from both purchase and delivery;
        # retain both intervals so policy-basis differences stay explicit.
        days=rng.randint(max(31,(delivery-purchase).days+31),60) if o['order_id'] in overdue else rng.randint((delivery-purchase).days,30)
        requested=(purchase+timedelta(days=days)).isoformat()
        claim=f"The {o['product_category']} has {defect}."
        photo=f"images/{o['order_id']}{p.suffix}"
        shutil.copy2(p,out/photo)
        row=dict(order_id=o['order_id'],source_image_id=evidence['source_image_id'],source_dataset=evidence['source_dataset'],image=photo,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),simulated_claim=claim,purchase_date=o['purchase_date'],delivery_date=o['delivery_date'],request_date=requested)
        row.update(days_since_purchase=days,days_since_delivery=days-(delivery-purchase).days,date_scenario='over_30_days' if o['order_id'] in overdue else 'within_30_days')
        try:
            service=SessionRefundService(runtime,order_source=out/'orders_snapshot.json')
            record=service.create(dict(order_id=o['order_id'],request_date=requested,submitted_purchase_date=o['purchase_date'],claim_text=claim,relevant_region_visible=True,image_base64=base64.b64encode(p.read_bytes()).decode()))
            row['result']=record['assessments'][0]['result']
            row['date_check']=record['assessments'][0]['date_check']
            row['decision']=row['result']['decision']['decision']
            row['reason']=row['result']['decision']['reason']
        except Exception as exc:
            row.update(decision='EXECUTION_ERROR',reason=str(exc))
        rows.append(row)
        print(row['order_id'],row['decision'],row['reason'],flush=True)
        (out/'results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
    summary=dict(total=len(rows),counts=dict(Counter(r['decision'] for r in rows)),reasons=dict(Counter(r['reason'] for r in rows)),auto_orders=[r['order_id'] for r in rows if r['decision']=='AUTO_REFUND'],seconds=time.monotonic()-started,weights_sha256=hashlib.sha256((root/'models/member2/best.pt').read_bytes()).hexdigest(),limitations='Integration test, not independent accuracy. Existing synthetic orders unchanged. Claims use source damage category; labels provisional, training overlap not excluded. Relevant region visibility assumed true. Request date is delivery plus 10 days. No manual approval or payment. Auto decisions not independently visually validated.')
    summary['limitations']=summary['limitations'].replace('Request date is delivery plus 10 days.', 'Random synthetic request dates: all 70 within 30 days of purchase and not before delivery; seed 32933. Policy rules unchanged.')
    summary['date_scenarios']={group:dict(Counter(r['decision'] for r in rows if r['date_scenario']==group)) for group in ('within_30_days','over_30_days')}
    summary['random_seed']=32933
    summary['order_scenario']='synthetic_delivered_not_final_sale' if normal_scenario else 'original_orders'
    summary['category_review']='Existing categories retained, NOT visually verified; this run does not correct category pairing.'
    if '--photo-matched' in sys.argv:
        summary['category_review']='Assistant visual review, not human ground truth; Unknown retained for ambiguous photos. No model predictions used for order categories.'
        summary['order_source']=str(source.relative_to(root))
    (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
    cards=[]
    for r in rows:
        m=r.get('result',{}).get('member2',{})
        text=f"{r['order_id']} / {r['source_image_id']} — {r['decision']}\n{r['reason']}\n{r['simulated_claim']}\nPrediction: {m.get('damage_type')} ({m.get('damage_confidence')})\nProduct: {m.get('detected_product')}"
        cards.append(f'<article><img loading="lazy" src="{r["image"]}"><pre>{html.escape(text)}</pre></article>')
    (out/'report.html').write_text('<!doctype html><meta charset="utf-8"><title>Member 2 — 70 photos</title><style>body{font:16px system-ui;margin:30px}article{display:flex;gap:20px;border-bottom:1px solid #ddd;padding:20px}img{width:230px;height:270px;object-fit:contain}pre{white-space:pre-wrap}</style><h1>Member 2 — ORD001–ORD070</h1><pre>'+html.escape(json.dumps(summary,ensure_ascii=False,indent=2))+'</pre>'+''.join(cards))
    print('SUMMARY',json.dumps(summary),flush=True)
    print('OUTPUT',out,flush=True)


if __name__=='__main__':
    main()
