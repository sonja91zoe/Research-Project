"""Workflow tests use an explicit controlled pipeline, not real CLIP accuracy."""
import base64
from io import BytesIO
from pathlib import Path
import pytest
from PIL import Image
from app.refund_service import RefundService
import src.damage_detection.runtime as runtime_config
from src.damage_detection.product import ProductTypeClassifier
from src.damage_detection.yolo import YoloBackend


def payload():
    b=BytesIO();Image.new('RGB',(20,20),'white').save(b,format='PNG')
    return dict(order_id='ORD003',claim_text='The white T-shirt has a stain.',request_date='2026-08-15',confidence_method='rule',relevant_region_visible=True,image_base64=base64.b64encode(b.getvalue()).decode())


def pipeline(decision):
    def run(case,**kwargs):
        assert Path(case.image_paths[0]).read_bytes().startswith(b'\x89PNG')
        return {'decision': {'decision': decision, 'reason': 'Controlled test'},'missing_evidence':[]}
    return run


def test_local_http_service_uses_canonical_runtime(tmp_path, monkeypatch):
    from app import refund_service

    monkeypatch.delenv(runtime_config.YOLO_WEIGHTS_ENV, raising=False)
    monkeypatch.setattr(runtime_config, 'find_spec', lambda name: object())
    received = {}

    def fake_pipeline(case, **kwargs):
        received.update(kwargs)
        return {'decision': {'decision': 'REQUEST_MORE_EVIDENCE'}}

    monkeypatch.setattr(refund_service, 'run_pipeline', fake_pipeline)
    refund_service.RefundService(tmp_path).create(payload())

    assert isinstance(received['detector'].backend, YoloBackend)
    assert isinstance(received['product_classifier'], ProductTypeClassifier)


def test_local_http_result_preserves_quality_gate_metadata(tmp_path):
    request = payload()
    request['relevant_region_visible'] = False

    record = RefundService(tmp_path).create(request)

    metadata = record['assessments'][0]['result']['member2']['runtime_metadata']
    assert metadata['damage_backend'] == 'yolo'
    assert metadata['product_classifier_backend'] == 'clip'
    assert metadata['damage_inference_completed'] is False
    assert metadata['product_classification_completed'] is False


def test_upload_reassess_history_and_restart(tmp_path):
    s=RefundService(tmp_path,pipeline('REQUEST_MORE_EVIDENCE'))
    r=s.create(payload());first=r['assessments'][0]
    s.pipeline=pipeline('HUMAN_REVIEW');r=s.evidence(r['case_id'],payload())
    assert len(r['assessments'])==2 and r['assessments'][0]==first
    assert RefundService(tmp_path).get(r['case_id'])==r
    assert s.image(r['case_id'],0)[0].startswith(b'\x89PNG')
    with pytest.raises(ValueError):s.confirm(r['case_id'])


def test_review_does_not_rewrite_agent_and_confirmation_idempotent(tmp_path):
    s=RefundService(tmp_path,pipeline('HUMAN_REVIEW'));r=s.create(payload())
    with pytest.raises(ValueError):s.review(r['case_id'],{'action':'APPROVE','reviewer':'','note':''})
    r=s.review(r['case_id'],dict(action='APPROVE',reviewer='Test reviewer',note='Controlled approval'))
    assert r['assessments'][0]['result']['decision']['decision']=='HUMAN_REVIEW'
    r=s.confirm(r['case_id']);assert r['status']=='SIMULATED_REFUNDED'
    assert s.confirm(r['case_id'])==r
    with pytest.raises(ValueError):s.evidence(r['case_id'],payload())
    with pytest.raises(ValueError):s.review(r['case_id'],dict(action='REJECT',reviewer='A',note='B'))


@pytest.mark.parametrize('action,status',[('REJECT','REJECTED'),('REQUEST_MORE_EVIDENCE','NEEDS_EVIDENCE')])
def test_review_outcomes(tmp_path,action,status):
    s=RefundService(tmp_path,pipeline('HUMAN_REVIEW'));r=s.create(payload())
    assert s.review(r['case_id'],dict(action=action,reviewer='A',note='B'))['status']==status
    with pytest.raises(ValueError):s.confirm(r['case_id'])


def test_auto_refund(tmp_path):
    s=RefundService(tmp_path,pipeline('AUTO_REFUND'));r=s.create(payload())
    assert s.confirm(r['case_id'])['status']=='SIMULATED_REFUNDED'


@pytest.mark.parametrize('change',[{'image_base64':'bad!'}, {'image_base64':base64.b64encode(b'not an image').decode()}, {'relevant_region_visible':'true'},{'request_date':'bad'},{'confidence_method':'anything'},{'claim_text':''}])
def test_invalid_input_leaves_no_result(tmp_path,change):
    s=RefundService(tmp_path,pipeline('AUTO_REFUND'));p=payload();p.update(change)
    with pytest.raises(ValueError):s.create(p)
    assert s.list()==[]


def test_pipeline_failure_preserves_previous_result(tmp_path):
    s=RefundService(tmp_path,pipeline('REQUEST_MORE_EVIDENCE'));r=s.create(payload())
    def fail(*args,**kwargs):raise RuntimeError('model unavailable')
    s.pipeline=fail
    with pytest.raises(RuntimeError):s.evidence(r['case_id'],payload())
    assert s.get(r['case_id'])==r
    assert len(list(tmp_path.glob('*/*.png')))==1


def test_invalid_case_path(tmp_path):
    s=RefundService(tmp_path)
    with pytest.raises(ValueError):s.get('../../anything')


def test_http_serves_only_ui_and_validated_api(tmp_path,monkeypatch):
    from http.server import ThreadingHTTPServer
    from http.client import HTTPConnection
    import threading,json
    from app import server
    monkeypatch.setattr(server,'SERVICE',RefundService(tmp_path,pipeline('AUTO_REFUND')))
    http=ThreadingHTTPServer(('127.0.0.1',0),server.RefundAppHandler)
    thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
    def request(method,path,body=None,headers=None):
        conn=HTTPConnection('127.0.0.1',http.server_port)
        conn.request(method,path,json.dumps(body) if body is not None else None,headers or {})
        r=conn.getresponse();data=r.read();conn.close();return r.status,data
    try:
        assert request('GET','/')[0]==200
        assert request('GET','/.git/config')[0]==404
        assert request('GET','/data/orders/orders.json')[0]==404
        assert request('POST','/api/cases',payload(),{'Content-Type':'application/json','Origin':'http://evil.example'})[0]==403
        status,body=request('POST','/api/cases',payload(),{'Content-Type':'application/json'})
        assert status==200
        record=json.loads(body)
        assert request('GET',f"/api/cases/{record['case_id']}/images/0")[0]==200
        assert request('POST',f"/api/cases/{record['case_id']}/confirm",{}, {'Content-Type':'application/json'})[0]==200
    finally:
        http.shutdown();http.server_close();thread.join()
