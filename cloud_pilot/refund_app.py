"""Streamlit entrypoint for the session-isolated refund demonstration."""
import base64
from dataclasses import asdict
from datetime import date
from datetime import datetime
from zoneinfo import ZoneInfo
import json
from pathlib import Path
import sys
import os

ROOT = Path(__file__).resolve().parents[1]
# Streamlit adds the entrypoint directory, which also contains app.py.
# Put the repository package ahead of that similarly named module.
if str(ROOT) in sys.path:
    sys.path.remove(str(ROOT))
sys.path.insert(0, str(ROOT))

import streamlit as st
from cloud_pilot.core import Runtime
from cloud_pilot.workflow import SessionRefundService
from cloud_pilot.presentation import evidence_summary
from src.evidence.order import load_orders

st.set_page_config(page_title='Refund Studio', page_icon='◇', layout='centered')

@st.cache_resource(show_spinner=False)
def runtime():
    return Runtime()

# The shared Member 2 demo catalog is stable. Zenodo artifacts are a
# separate evaluation set and must never silently replace the demo orders.
ORDER_SOURCE = ROOT / 'data/orders/orders.json'

local_database = os.getenv('REFUND_LOCAL_CASE_DB')
catalog_key = (str(ORDER_SOURCE), local_database)
if ('refund_workflow' not in st.session_state
        or st.session_state.get('refund_catalog_key') != catalog_key):
    if local_database:
        from cloud_pilot.persistent_workflow import LocalSqliteRefundService
        st.session_state.refund_workflow = LocalSqliteRefundService(
            runtime(), local_database, order_source=ORDER_SOURCE)
    elif 'refund_workflow' in st.session_state:
        # Keep in-session cases when the source changes after a hot reload.
        st.session_state.refund_workflow.order_source = ORDER_SOURCE
    else:
        st.session_state.refund_workflow = SessionRefundService(runtime(), order_source=ORDER_SOURCE)
    st.session_state.refund_catalog_key = catalog_key
service = st.session_state.refund_workflow
LABELS = {'READY_TO_REFUND': 'Ready to confirm simulated refund',
          'NEEDS_EVIDENCE': 'More evidence needed', 'PENDING_REVIEW': 'Awaiting human review',
          'REJECTED': 'Declined in demonstration', 'SIMULATED_REFUNDED': 'Simulated refund completed'}

def photo_payload(upload, visible):
    if upload is None:
        raise ValueError('Choose a JPEG or PNG photo.')
    if visible == 'Please select':
        raise ValueError('Specify whether the claimed area is visible.')
    return {'image_base64': base64.b64encode(upload.getvalue()).decode('ascii'),
            'relevant_region_visible': visible == 'Yes'}

def act(callback):
    try:
        with st.spinner('Processing your application. The first image analysis may take longer.'):
            record = callback()
        st.session_state.active_refund = record['case_id']
    except Exception as error:
        st.error(f'Could not complete this action: {error}')
        return
    st.rerun()

st.title('Refund Studio')
st.write('Submit an application → Analyze evidence → Decision and follow-up')
st.info('Research demonstration only. No payments. Review actions below are role-play, without reviewer authentication.')
if local_database:
    st.warning('Local single-user database mode: new uploaded photos and application history persist across restarts. Older imported cases may lack photos. Do not enable this mode on a public server without authentication.')
else:
    st.caption('Uses real image analysis and rule-based Agent scoring. Missing visual evidence remains missing. Records belong to this browser session; refreshing or restarting may lose them. Download records to keep them.')

orders = [asdict(order) for order in load_orders(ORDER_SOURCE).values()]
st.caption('Demo catalog: Member 2 photos · ORD001–ORD070. Zenodo evaluation orders are separate; historical applications retain their original IDs.')
by_id = {o['order_id']: o for o in orders}
rows = service.list()
choices = ['New application'] + [r['case_id'] for r in rows]
active = st.session_state.get('active_refund')
selected = st.selectbox('Your session applications', choices,
    index=choices.index(active) if active in choices else 0,
    format_func=lambda x: x if x == 'New application' else
        f"{service.get(x)['order_id']} · {LABELS[service.get(x)['status']]} · {x[:8]}")

if selected == 'New application':
    st.subheader('Start a refund application')
    order_id = st.selectbox('Demo order', list(by_id))
    order = by_id[order_id]
    st.caption(f"Amount: {order['price']} · Purchased: {order['purchase_date']}")
    st.info(f"模擬訂單日期／Demo dates — {order_id}\n\n"
            f"購買日期 Purchase date：{order['purchase_date']}\n\n"
            f"收貨日期 Delivery date：{order.get('delivery_date') or '未提供／Unknown'}\n\n"
            '購買日期已自動填入，收貨日期由訂單讀取，不需自行猜測。這些日期是模擬資料，不是真實交易證明。')
    evidence = order.get('image_evidence') or {}
    reference_path = evidence.get('image_path')
    if reference_path:
        reference_image = Path(reference_path)
        if not reference_image.is_absolute():
            reference_image = ROOT / reference_image
        if reference_image.is_file():
            st.image(str(reference_image), caption='Order reference photo')
    if evidence:
        st.caption(
            'Reference source: '
            f"{evidence.get('source_dataset', 'Unknown')} · "
            f"ID {evidence.get('source_image_id', 'Unknown')} · "
            f"License {evidence.get('license', 'Unknown')}"
        )
        st.caption(
            'The photo and garment annotation are source evidence. Price, '
            'dates, delivery status and retailer are simulated.'
        )
    with st.form('create_refund'):
        st.write('Request date')
        today = datetime.now(ZoneInfo('Australia/Sydney')).date()
        months = ('January', 'February', 'March', 'April', 'May', 'June',
                  'July', 'August', 'September', 'October', 'November', 'December')
        year_col, month_col, day_col = st.columns(3)
        requested_year = year_col.number_input('Year', min_value=1900, max_value=2100,
                                               value=today.year, step=1)
        requested_month = month_col.selectbox('Month', list(range(1, 13)),
                                              index=today.month - 1,
                                              format_func=lambda m: months[m - 1])
        requested_day = day_col.selectbox('Day', list(range(1, 32)), index=today.day - 1)
        st.caption('Use a valid calendar date, for example 15 August 2026.')
        st.caption('For historical demonstrations, select the actual demonstration date. Policy checks use this date.')
        st.info(f'申請日期 Request date：測試「今天申請」請用 {today.isoformat()}（雪梨時間）。'
                f"若只測試收貨當天的歷史情境，可明確選用 {order.get('delivery_date') or '已確認的收貨日期'}。"
                '日期不同可能影響政策結果，不保證自動退款；不要為了通過而假填日期。')
        purchase_date = st.text_input('Purchase date to verify (YYYY-MM-DD)', value=order['purchase_date'],
            key='purchase_date_' + order_id, help='Pre-filled from the synthetic order; editable to test mismatches.')
        claim = st.text_area('Describe the product, damage and location in English', max_chars=3000)
        uploaded = st.file_uploader('Product photo (JPEG / PNG, maximum 8 MB)', type=['jpg', 'jpeg', 'png'])
        visible = st.selectbox('Is the claimed area visible?', ['Please select', 'Yes', 'No'])
        submitted = st.form_submit_button('Submit and analyze')
    if submitted:
        act(lambda: service.create({'order_id': order_id, 'request_date': date(int(requested_year), requested_month, requested_day).isoformat(),
                                    'submitted_purchase_date': purchase_date,
                                    'claim_text': claim, **photo_payload(uploaded, visible)}))
else:
    record = service.get(selected)
    result = record['assessments'][-1]['result']
    st.subheader(LABELS[record['status']])
    st.write(f"Order {record['order_id']} · Request date {record['request_date']}")
    st.write('Claim:', record['claim_text'])
    st.write('Automated assessment for this photo:', result['decision']['reason'])
    summary = evidence_summary(result)
    st.subheader('Evidence summary')
    st.write('Model product prediction:', summary['product'])
    if summary['product_confidence'] is not None:
        st.write('Product prediction score:', f"{summary['product_confidence']:.3f}")
    st.write('Predicted product category compared with order category:', summary['order_match'])
    st.caption('Category match is not proof that this is the exact purchased item. The product model can misclassify a photo.')
    st.write('Purchase-date check:', record['assessments'][-1].get('date_check', {}).get('status', 'NOT_PROVIDED'))
    if record['status'] not in {'SIMULATED_REFUNDED', 'REJECTED'}:
        with st.expander('Correct order, description or dates and reassess'):
            st.caption('Upload the intended photo again. Previous inputs and assessments are retained; any previous approval is reassessed.')
            with st.expander('訂單日期對照／Order date reference'):
                st.table([{'Order': o['order_id'], 'Purchase date': o['purchase_date'],
                           'Delivery date': o.get('delivery_date') or 'Unknown'} for o in orders])
            with st.form('correct_' + selected):
                corrected_order = st.selectbox('Corrected order', list(by_id), index=list(by_id).index(record['order_id']) if record['order_id'] in by_id else 0)
                corrected_claim = st.text_area('Corrected description', value=record['claim_text'], max_chars=3000)
                corrected_request = st.text_input('Corrected request date (YYYY-MM-DD)', value=record['request_date'])
                corrected_purchase = st.text_input('Purchase date to verify (YYYY-MM-DD)', value=record.get('submitted_purchase_date', ''))
                corrected_photo = st.file_uploader('Photo for corrected application (maximum 8 MB)', type=['jpg', 'jpeg', 'png'])
                corrected_visible = st.selectbox('Claimed area visible in corrected photo?', ['Please select', 'Yes', 'No'])
                correct_submit = st.form_submit_button('Save corrections and reassess')
            if correct_submit:
                act(lambda: service.amend(selected, {'order_id': corrected_order, 'claim_text': corrected_claim,
                    'request_date': corrected_request, 'submitted_purchase_date': corrected_purchase,
                    **photo_payload(corrected_photo, corrected_visible)}))
    st.write('Model damage prediction:', summary['damage'])
    st.write('Detected damage location:', summary['location'])
    st.write('Description compared with the photo:', summary['verdict'])
    st.write(summary['reason'])
    st.caption('A model prediction can be wrong. Damage scores are not probabilities of refund eligibility.')
    quality, policy = result.get('member1', {}), result.get('member3', {})
    st.write('Photo usable:', 'Yes' if quality.get('image_usable') else 'No')
    st.write('Order validated:', 'Yes' if policy.get('order_valid') else 'No')
    st.write('綜合退款資格／Overall eligibility:', '已確認／Confirmed' if policy.get('policy_eligible') else '尚未確認／Not confirmed')
    chain = result.get('evidence_chain', {})
    stored_order = chain.get('order_evidence') or {}
    retrieved_policy = chain.get('policy_evidence') or {}
    st.write('訂單配送狀態／Delivery status:', stored_order.get('status', 'Unknown'))
    start_date = stored_order.get('delivery_date') or stored_order.get('purchase_date')
    if start_date and result.get('request_date') and retrieved_policy.get('refund_window_days') is not None:
        elapsed = (date.fromisoformat(result['request_date']) - date.fromisoformat(start_date)).days
        window = retrieved_policy['refund_window_days']
        st.write('政策日期檢查／Date window:', f'{elapsed} days / {window} days — ' + ('期限內' if 0 <= elapsed <= window else '不在期限內'))
        st.caption('目前政策從收貨日計算；缺少收貨日時才使用購買日。期限內不代表所有退款條件均符合。')
    st.write('資格檢查詳細原因／Eligibility reason:', (chain.get('verified_evidence') or {}).get('reason') or 'Not available')
    st.caption('圖片證據不足不等於日期超期；模型預測、訂單條件與最終資格分開呈現。')
    st.write('Missing evidence:', ', '.join(summary['missing']) or 'None reported')
    if summary['missing']:
        st.info('A clearer photo may help with visual evidence, but does not guarantee that this model can identify the product or location. Demo review approval preserves these unresolved gaps.')
    if record['status'] == 'NEEDS_EVIDENCE':
        st.write('Upload a clearer photo of the same product and claimed damage. Previous assessments remain in the history.')
        with st.form('supplement_' + selected):
            uploaded = st.file_uploader('New evidence photo (maximum 8 MB)', type=['jpg', 'jpeg', 'png'])
            visible = st.selectbox('Is the claimed area visible?', ['Please select', 'Yes', 'No'])
            submitted = st.form_submit_button('Add evidence and reassess')
        if submitted:
            act(lambda: service.evidence(selected, photo_payload(uploaded, visible)))
    elif record['status'] == 'PENDING_REVIEW':
        st.write('Human review demonstration. A review records a separate decision; it does not resolve missing model evidence.')
        with st.form('review_' + selected):
            reviewer = st.text_input('Demo reviewer name', max_chars=2000)
            action = st.selectbox('Review decision', ['REQUEST_MORE_EVIDENCE', 'APPROVE', 'REJECT'],
                                  format_func=lambda action: {'REQUEST_MORE_EVIDENCE': 'Request more evidence', 'APPROVE': 'Approve for simulated refund', 'REJECT': 'Decline in demonstration'}[action])
            note = st.text_area('人工審核回饋 / Reviewer feedback (required)', max_chars=2000,
                height=150,
                placeholder='例如：請補上破洞近照；或說明同意／拒絕模擬退款的原因。',
                help='回饋會隨審核決定保存於案件紀錄及下載的 JSON；不會改寫模型預測。')
            submitted = st.form_submit_button('Save demo review')
        if submitted:
            act(lambda: service.review(selected, {'reviewer': reviewer, 'action': action, 'note': note}))
    elif record['status'] == 'READY_TO_REFUND':
        st.warning('Confirmation records a simulated refund only. No money will be transferred.')
        if st.button('Confirm simulated refund'):
            act(lambda: service.confirm(selected))
    elif record['status'] == 'SIMULATED_REFUNDED':
        st.success('Workflow complete. No money was transferred.')
    review_events = [event for event in record['events']
                     if event['action'].startswith('HUMAN_')]
    st.subheader('人工審核回饋 / Reviewer feedback')
    if not review_events:
        st.caption('尚無人工審核回饋 / No reviewer feedback yet.')
    for event in reversed(review_events):
        with st.container(border=True):
            st.caption(f"{event['at']} · {event.get('reviewer', '')} · {event['action']}")
            st.text(event.get('note', ''))
    with st.expander('Full evidence and original Agent assessment'):
        st.json(result)
    st.subheader('Application history')
    if local_database:
        with st.expander('Saved evidence photos by assessment'):
            for revision, assessment in enumerate(record['assessments']):
                if assessment.get('image_sha256'):
                    data, _ = service.image(selected, revision)
                    st.image(data, caption=f'Assessment {revision + 1}: uploaded photo')
                else:
                    st.caption(f'Assessment {revision + 1}: historical image not retained.')
    for event in record['events']:
        st.write(f"{event['at']} · {event['action'].replace('_', ' ').title()} · {LABELS[event['status']]}")
        if event.get('reviewer'):
            st.write('Reviewer:', event['reviewer'])
        if event.get('note'):
            st.write(event['note'])
    st.download_button('Download application record', json.dumps(record, indent=2),
                       file_name=f"refund_{selected}.json", mime='application/json')
