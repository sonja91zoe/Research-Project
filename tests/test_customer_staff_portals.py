"""Controlled routing and permissions checks; no claims about model accuracy."""
import json
import threading
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from types import SimpleNamespace as NS
import pytest
from app.portal_service import PortalService, DEMO_ACCOUNT
from tests.test_student4_web_workflow import payload, pipeline
from src.decision.decision import make_decision

@pytest.mark.parametrize('match,decision',[('MISMATCH','REJECT_REFUND'),('NOT_AVAILABLE','HUMAN_REVIEW')])
def test_product_outcomes_override_auto(match,decision):
    m1=NS(image_usable=True,relevant_region_visible=True)
    m3=NS(order_valid=True,image_order_match_status=match)
    assert make_decision('HIGH','LOW',m1,NS(),m3)[0]==decision

@pytest.mark.parametrize('decision,status',[('AUTO_REFUND','SIMULATED_REFUNDED'),('REJECT_REFUND','REJECTED'),('HUMAN_REVIEW','PENDING_REVIEW')])
def test_automatic_routes_and_account(tmp_path,decision,status):
    s=PortalService(tmp_path,pipeline(decision))
    r=s.create_for(DEMO_ACCOUNT,payload())
    assert r['status']==status and r['account_id']==DEMO_ACCOUNT
    assert s.records('someone_else')==[]
    with pytest.raises(PermissionError):s.owned('someone_else',r['case_id'])
    assert PortalService(tmp_path).get(r['case_id'])['account_id']==DEMO_ACCOUNT

@pytest.mark.parametrize('action,status',[('APPROVE','SIMULATED_REFUNDED'),('REJECT','REJECTED'),('REQUEST_MORE_EVIDENCE','NEEDS_EVIDENCE')])
def test_staff_decisions_preserve_assessment(tmp_path,action,status):
    s=PortalService(tmp_path,pipeline('HUMAN_REVIEW'));r=s.create_for(DEMO_ACCOUNT,payload())
    original=r['assessments'][0]
    reviewed=s.staff_review(r['case_id'],{'action':action,'reviewer':'Staff','note':'Reviewed photo'})
    assert reviewed['status']==status and reviewed['assessments'][0]==original
    if action=='REQUEST_MORE_EVIDENCE':
        s.pipeline=pipeline('HUMAN_REVIEW');again=s.evidence(r['case_id'],payload())
        assert again['status']=='PENDING_REVIEW' and len(again['assessments'])==2
        assert again['account_id']==DEMO_ACCOUNT


def test_http_login_ownership_and_review_isolation(tmp_path,monkeypatch):
    from app import server
    monkeypatch.setattr(server,'SERVICE',PortalService(tmp_path,pipeline('HUMAN_REVIEW')))
    monkeypatch.setattr(server,'SESSIONS',{})
    http=ThreadingHTTPServer(('127.0.0.1',0),server.RefundAppHandler)
    worker=threading.Thread(target=http.serve_forever,daemon=True);worker.start()
    def req(method,path,data=None,cookie=None,origin=None):
        conn=HTTPConnection('127.0.0.1',http.server_port)
        headers={'Content-Type':'application/json'}
        if cookie:headers['Cookie']=cookie
        if origin:headers['Origin']=origin
        conn.request(method,path,json.dumps(data) if data is not None else None,headers)
        response=conn.getresponse();body=response.read();session=response.getheader('Set-Cookie');status=response.status;conn.close()
        return status,body,session.split(';')[0] if session else None
    try:
        assert req('GET','/customer')[0]==200 and req('GET','/staff')[0]==200
        assert req('GET','/api/orders')[0]==403
        assert req('POST','/api/login',{'account':DEMO_ACCOUNT,'password':'wrong'})[0]==403
        code,body,cookie=req('POST','/api/login',{'account':DEMO_ACCOUNT,'password':'Refund123!'})
        assert code==200
        assert len(json.loads(req('GET','/api/orders',cookie=cookie)[1]))==70
        code,body,_=req('POST','/api/cases',payload(),cookie)
        assert code==200;r=json.loads(body);id=r['case_id']
        assert req('GET','/api/cases/'+id)[0]==403
        assert req('GET','/api/staff/cases',cookie=cookie)[0]==403
        action={'action':'REQUEST_MORE_EVIDENCE','reviewer':'Staff','note':'Need a close-up'}
        assert req('POST',f'/api/staff/cases/{id}/review',action,cookie)[0]==403
        assert req('POST','/api/staff/session',{},origin='http://evil.test')[0]==403
        staff=req('POST','/api/staff/session',{})[2]
        assert len(json.loads(req('GET','/api/staff/cases',cookie=staff)[1]))==1
        code,body,_=req('POST',f'/api/staff/cases/{id}/review',action,staff)
        assert code==200 and json.loads(body)['status']=='NEEDS_EVIDENCE'
        code,body,_=req('POST',f'/api/cases/{id}/evidence',payload(),cookie)
        assert code==200 and json.loads(body)['status']=='PENDING_REVIEW'
        assert req('GET',f'/api/cases/{id}/images/0',cookie=cookie)[0]==200
        assert req('GET','/.git/config')[0]==404
        assert req('POST','/api/logout',{},cookie)[0]==200
        assert req('GET','/api/cases',cookie=cookie)[0]==403
    finally:http.shutdown();http.server_close();worker.join()
