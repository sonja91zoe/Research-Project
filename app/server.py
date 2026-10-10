"""Local customer and staff portals sharing one persistent refund workflow."""
import hmac
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import threading
import time
from urllib.parse import urlsplit
from app.portal_service import PortalService, DEMO_ACCOUNT, DEMO_PASSWORD

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SERVICE = PortalService()
SESSIONS = {}
SESSION_LOCK = threading.RLock()

class RefundAppHandler(BaseHTTPRequestHandler):
    def _send(self, status, body, content_type, cookie=None):
        self.send_response(status)
        for k,v in [('Content-Type',content_type),('Content-Length',str(len(body))),('Cache-Control','no-store'),('X-Content-Type-Options','nosniff'),('Content-Security-Policy',"default-src 'self'; img-src 'self' blob:; style-src 'self' 'unsafe-inline'; script-src 'self'")]:
            self.send_header(k,v)
        if cookie: self.send_header('Set-Cookie',cookie)
        self.end_headers(); self.wfile.write(body)

    def _json(self, status, data, cookie=None):
        self._send(status,json.dumps(data,ensure_ascii=False).encode(),'application/json; charset=utf-8',cookie)

    def _local(self):
        allowed={f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'}
        if self.headers.get('Host') not in allowed or (self.headers.get('Origin') and self.headers['Origin'] not in {'http://'+h for h in allowed}):
            self._json(403,{'error':'Only same-origin local requests are accepted.'}); return False
        return True

    def _session(self, role):
        cookies=SimpleCookie(self.headers.get('Cookie',''))
        c=cookies.get('refund_'+role)
        with SESSION_LOCK:
            session=SESSIONS.get(c.value if c else '')
            if not session or session['role']!=role or session['expires']<time.time():
                raise PermissionError('Please sign in first.' if role=='customer' else 'Open the staff portal first.')
            return session['account']

    def _login(self, role, account):
        token=secrets.token_urlsafe(32)
        with SESSION_LOCK: SESSIONS[token]={'role':role,'account':account,'expires':time.time()+28800}
        self._json(200,{'account':account},f'refund_{role}={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800')

    def do_GET(self):
        if not self._local(): return
        path=urlsplit(self.path).path
        assets={'/':'customer.html','/customer':'customer.html','/staff':'staff.html','/app/risk_aware_refund_ui.html':'customer.html','/portal.css':'portal.css','/customer.js':'customer.js','/staff.js':'staff.js','/portal-common.js':'portal-common.js'}
        try:
            if path in assets:
                mime='text/javascript' if path.endswith('.js') else 'text/css' if path.endswith('.css') else 'text/html'
                self._send(200,(PROJECT_ROOT/'app'/assets[path]).read_bytes(),mime+'; charset=utf-8'); return
            if path=='/api/me': self._json(200,{'account':self._session('customer')}); return
            if path=='/api/orders': self._json(200,SERVICE.orders_for(self._session('customer'))); return
            if path=='/api/cases': self._json(200,SERVICE.records(self._session('customer'))); return
            if path=='/api/staff/cases':
                self._session('staff'); self._json(200,SERVICE.records()); return
            parts=path.strip('/').split('/')
            staff=len(parts)>1 and parts[1]=='staff'
            if staff: parts.pop(1)
            if len(parts)>=3 and parts[:2]==['api','cases']:
                account=self._session('staff' if staff else 'customer')
                record=SERVICE.get(parts[2]) if staff else SERVICE.owned(account,parts[2])
                if len(parts)==3: self._json(200,record); return
                if len(parts)==5 and parts[3]=='images':
                    body,mime=SERVICE.image(parts[2],int(parts[4]));self._send(200,body,mime);return
            self._json(404,{'error':'Not found.'})
        except PermissionError as e: self._json(403,{'error':str(e)})
        except (ValueError,FileNotFoundError,IndexError): self._json(404,{'error':'Application or evidence not found.'})

    def do_POST(self):
        if not self._local(): return
        try:
            length=int(self.headers.get('Content-Length','0'))
            if length<=0 or length>12*1024*1024: self._json(413,{'error':'Request is empty or too large.'});return
            if self.headers.get_content_type()!='application/json': self._json(415,{'error':'JSON is required.'});return
            payload=json.loads(self.rfile.read(length))
            if not isinstance(payload,dict): raise ValueError('A JSON object is required.')
            path=urlsplit(self.path).path
            if path=='/api/login':
                if payload.get('account')!=DEMO_ACCOUNT or not isinstance(payload.get('password'),str) or not hmac.compare_digest(payload['password'],DEMO_PASSWORD):
                    self._json(403,{'error':'Incorrect account or password.'});return
                self._login('customer',DEMO_ACCOUNT);return
            if path=='/api/staff/session': self._login('staff','Staff');return
            if path=='/api/logout':
                cookies=SimpleCookie(self.headers.get('Cookie',''))
                with SESSION_LOCK:
                    if cookies.get('refund_customer'): SESSIONS.pop(cookies['refund_customer'].value,None)
                self._json(200,{},'refund_customer=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0');return
            parts=path.strip('/').split('/')
            if parts==['api','cases']:
                result=SERVICE.create_for(self._session('customer'),payload)
            elif len(parts)==4 and parts[:2]==['api','cases'] and parts[3]=='evidence':
                SERVICE.owned(self._session('customer'),parts[2]);result=SERVICE.evidence(parts[2],payload)
            elif len(parts)==5 and parts[:3]==['api','staff','cases'] and parts[4]=='review':
                self._session('staff');result=SERVICE.staff_review(parts[3],payload)
            else: self._json(404,{'error':'Not found.'});return
            self._json(200,result)
        except PermissionError as e: self._json(403,{'error':str(e)})
        except FileNotFoundError: self._json(404,{'error':'Application not found.'})
        except (KeyError,TypeError,ValueError) as e: self._json(400,{'error':str(e)})
        except Exception:
            import traceback;traceback.print_exc()
            self._json(500,{'error':'Processing failed. Check model availability in the server terminal and retry.'})

    def do_HEAD(self): self._json(405,{'error':'Method not allowed.'})

def run_evidence_case(payload):
    from dataclasses import asdict
    from src.common.schemas import CaseInput, Member1Output, Member2Output, Member3Output
    from src.agent.agent import run_agent
    from src.evidence.pipeline import build_evidence_chain
    from src.evidence.rules import load_adopted_rules
    from src.image_quality.claim_parser import parse_claim

    case_id = payload.get("case_id", "UI-DEMO-001")
    detected_product = payload.get("detected_product") or None
    damage_type = payload.get("damage_type") or "hole_or_tear"
    image_usable = bool(payload.get("image_usable", True))

    case = CaseInput(
        case_id=case_id,
        order_id=payload["order_id"],
        claim_text=payload["claim_text"],
        image_paths=["browser-upload.jpg"] if payload.get("image_present", True) else [],
    )
    parsed_claim = parse_claim(payload["claim_text"])
    member1 = Member1Output(
        case_id=case_id,
        product=parsed_claim["product"],
        claimed_defect=parsed_claim["claimed_defect"],
        claimed_location=parsed_claim["claimed_location"],
        image_quality=float(payload.get("image_quality", 0.90)),
        blur_score=0.10,
        lighting_score=0.91,
        relevant_region_visible=image_usable,
        image_usable=image_usable,
    )
    member2 = Member2Output(
        case_id=case_id,
        detected_product=detected_product,
        product_confidence=(
            float(payload["product_confidence"])
            if payload.get("product_confidence") is not None
            else None
        ),
        damage_detected=bool(payload.get("damage_detected", True)),
        damage_type=damage_type,
        damage_location=payload.get("damage_location", "left sleeve"),
        damage_confidence=float(payload.get("damage_confidence", 0.88)),
        claim_image_consistency=float(payload.get("claim_image_consistency", 0.92)),
    )
    chain = build_evidence_chain(
        case,
        member1,
        member2,
        payload.get("request_date", "2026-08-15"),
    )
    decision = run_agent(member1, member2, Member3Output(**chain.member3_output))
    return {
        "order": asdict(chain.order_evidence) if chain.order_evidence else None,
        "policy": asdict(chain.policy_evidence) if chain.policy_evidence else None,
        "adopted_rules": load_adopted_rules(),
        "evidence": chain.member3_output,
        "reason": chain.verified_evidence.reason,
        "decision": decision.model_dump(),
    }


def main():
    print('Customer portal: http://127.0.0.1:8765/customer')
    print('Staff portal: http://127.0.0.1:8765/staff')
    ThreadingHTTPServer(('127.0.0.1',8765),RefundAppHandler).serve_forever()

if __name__=='__main__': main()
