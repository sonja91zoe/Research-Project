"""Streamlit entrypoint for the session-isolated refund demonstration."""
import base64
from dataclasses import asdict
from datetime import date
import json
from pathlib import Path
import sys

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

TRACEABLE_ROOT = ROOT / 'artifacts/traceable_orders'
ORDER_SOURCE = (
    TRACEABLE_ROOT / 'orders.db'
    if (TRACEABLE_ROOT / 'orders.db').is_file()
    else ROOT / 'data/orders/orders.json'
)

if 'refund_workflow' not in st.session_state:
    st.session_state.refund_workflow = SessionRefundService(
        runtime(), order_source=ORDER_SOURCE
    )
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
st.caption('Uses real image analysis and rule-based Agent scoring. Missing visual evidence remains missing. Records belong to this browser session; refreshing or restarting may lose them. Download records to keep them.')

orders = [asdict(order) for order in load_orders(ORDER_SOURCE).values()]
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
    order_id = st.selectbox('Demo order', list(by_id),
                            format_func=lambda x: f"{x} · {by_id[x]['product_name']}")
    order = by_id[order_id]
    st.caption(f"Amount: {order['price']} · Purchased: {order['purchase_date']}")
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
        today = date.today()
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
        claim = st.text_area('Describe the product, damage and location in English', max_chars=3000)
        uploaded = st.file_uploader('Product photo (JPEG / PNG, maximum 8 MB)', type=['jpg', 'jpeg', 'png'])
        visible = st.selectbox('Is the claimed area visible?', ['Please select', 'Yes', 'No'])
        submitted = st.form_submit_button('Submit and analyze')
    if submitted:
        act(lambda: service.create({'order_id': order_id, 'request_date': date(int(requested_year), requested_month, requested_day).isoformat(),
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
    st.write('Photo compared with ordered product:', summary['order_match'])
    st.write('Model damage prediction:', summary['damage'])
    st.write('Detected damage location:', summary['location'])
    st.write('Description compared with the photo:', summary['verdict'])
    st.write(summary['reason'])
    st.caption('A model prediction can be wrong. Damage scores are not probabilities of refund eligibility.')
    quality, policy = result.get('member1', {}), result.get('member3', {})
    st.write('Photo usable:', 'Yes' if quality.get('image_usable') else 'No')
    st.write('Order validated:', 'Yes' if policy.get('order_valid') else 'No')
    st.write('Policy eligibility confirmed:', 'Yes' if policy.get('policy_eligible') else 'No')
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
            note = st.text_area('Review note and reason', max_chars=2000)
            submitted = st.form_submit_button('Save demo review')
        if submitted:
            act(lambda: service.review(selected, {'reviewer': reviewer, 'action': action, 'note': note}))
    elif record['status'] == 'READY_TO_REFUND':
        st.warning('Confirmation records a simulated refund only. No money will be transferred.')
        if st.button('Confirm simulated refund'):
            act(lambda: service.confirm(selected))
    elif record['status'] == 'SIMULATED_REFUNDED':
        st.success('Workflow complete. No money was transferred.')
    with st.expander('Full evidence and original Agent assessment'):
        st.json(result)
    st.subheader('Application history')
    for event in record['events']:
        st.write(f"{event['at']} · {event['action'].replace('_', ' ').title()} · {LABELS[event['status']]}")
        if event.get('reviewer'):
            st.write('Reviewer:', event['reviewer'])
        if event.get('note'):
            st.write(event['note'])
    st.download_button('Download application record', json.dumps(record, indent=2),
                       file_name=f"refund_{selected}.json", mime='application/json')
