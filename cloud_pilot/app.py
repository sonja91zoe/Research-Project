"""Run from repo root: python -m streamlit run cloud_pilot/app.py"""
from importlib.metadata import version
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
from cloud_pilot.core import Runtime, analyze

st.set_page_config(page_title='Refund Studio | Cloud Pilot', page_icon='🔎', layout='centered')


@st.cache_resource(show_spinner=False)
def runtime():
    # Only the model and its inference lock are shared. Never cache user results.
    return Runtime()


st.caption('REFUND STUDIO · CLOUD FEASIBILITY PILOT')
st.title('Test real image analysis')
st.write('Check whether this server can run image-quality checks and the real CLIP model.')
st.info('This first cloud pilot does not approve refunds or offer human review. It tests the image pipeline only.')

with st.form('image_test'):
    source = st.radio('Image source', ['Upload a photo', 'Bundled jacket example'])
    uploaded = st.file_uploader('Product photo (JPEG / PNG, up to 8 MB)', type=['jpg', 'jpeg', 'png'])
    claim = st.text_area('Describe the product, damage and location in English',
                         value='The jacket arrived with a tear on the left sleeve.', max_chars=3000)
    visible = st.selectbox('Is the claimed area visible?', ['Please select', 'Yes', 'No'])
    submitted = st.form_submit_button('Analyze image')

if submitted:
    st.session_state.pop('pilot_result', None)
    try:
        if visible == 'Please select':
            raise ValueError('Please specify whether the claimed area is visible.')
        if source == 'Upload a photo':
            if uploaded is None:
                raise ValueError('Please select a photo, or choose the bundled example.')
            data = uploaded.getvalue()
        else:
            data = (ROOT / 'data/member1/images/member1_jacket_001.jpg').read_bytes()
        with st.spinner('Checking the photo and running CLIP. The first run downloads and loads the model; please wait.'):
            result = analyze(data, claim, visible == 'Yes', runtime())
        result['image_source'] = source
        result['package_versions'] = {name: version(name) for name in ('streamlit', 'torch', 'transformers', 'pydantic', 'Pillow', 'numpy')}
        st.session_state['pilot_result'] = result
    except Exception as error:
        st.error(f'Analysis did not complete: {type(error).__name__}: {error}')
        st.caption('No result has been substituted. If the app restarts or runs out of memory, inspect the deployment logs.')

result = st.session_state.get('pilot_result')
if result:
    st.subheader('Last submitted image result')
    if result['clip_inference_completed']:
        st.success('Real CLIP inference completed on this server.')
    else:
        st.warning('Image quality or visibility did not pass. CLIP was skipped, so cloud model feasibility has not yet been demonstrated.')
    st.write('**Claim:**', result['claim_text'])
    st.write('**Image source:**', result['image_source'])
    cols = st.columns(3)
    cols[0].metric('Elapsed time', f"{result['elapsed_seconds']} s")
    cols[1].metric('Image usable', str(result['member1']['image_usable']))
    cols[2].metric('Damage class', result['member2']['damage_type'])
    st.caption('The damage score is a model score, not a calibrated probability of refund eligibility.')
    with st.expander('Full analysis', expanded=True):
        st.json(result)
    st.download_button('Download this result', json.dumps(result, indent=2),
                       file_name='cloud_image_pilot.json', mime='application/json')

st.caption('Temporary image files are removed after analysis. Results are kept only in this browser session and may be lost on reload or restart. Download a result to keep it. Use demonstration images.')
