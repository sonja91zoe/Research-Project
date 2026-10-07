"""Local web app for the risk-aware refund prototype."""

import json
import sys
from dataclasses import asdict
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.common.schemas import CaseInput, Member1Output, Member2Output, Member3Output
from src.agent.agent import run_agent
from src.evidence.pipeline import build_evidence_chain
from src.evidence.order import load_orders
from src.evidence.rules import load_adopted_rules


from urllib.parse import urlsplit
from app.refund_service import RefundService

SERVICE = RefundService()


class RefundAppHandler(SimpleHTTPRequestHandler):
    def _send(self, status, body, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, status, payload):
        self._send(status, json.dumps(payload, ensure_ascii=False).encode(), "application/json; charset=utf-8")

    def _local(self):
        host = self.headers.get('Host', '')
        allowed = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
        origin = self.headers.get('Origin')
        if host not in allowed or (origin and origin not in {'http://'+h for h in allowed}):
            self._send_json(403, {'error': 'Only same-origin local requests are accepted.'})
            return False
        return True

    def do_GET(self):
        if not self._local():
            return
        path = urlsplit(self.path).path
        try:
            if path in {'/', '/app/risk_aware_refund_ui.html'}:
                self._send(200, (PROJECT_ROOT/'app/risk_aware_refund_ui.html').read_bytes(), 'text/html; charset=utf-8')
            elif path == '/refund.js':
                self._send(200, (PROJECT_ROOT/'app/refund.js').read_bytes(), 'text/javascript; charset=utf-8')
            elif path == '/api/orders':
                self._send_json(200, json.loads((PROJECT_ROOT/'data/orders/orders.json').read_text()))
            elif path == '/api/cases':
                self._send_json(200, SERVICE.list())
            elif path.startswith('/api/cases/'):
                parts = path.strip('/').split('/')
                if len(parts) == 3:
                    self._send_json(200, SERVICE.get(parts[2]))
                elif len(parts) == 5 and parts[3] == 'images':
                    data, mime = SERVICE.image(parts[2], int(parts[4]))
                    self._send(200, data, mime)
                else:
                    self._send_json(404, {'error': 'Not found.'})
            else:
                self._send_json(404, {'error': 'Not found.'})
        except (FileNotFoundError, ValueError, IndexError):
            self._send_json(404, {'error': 'Application or evidence not found.'})

    def do_HEAD(self):
        self._send_json(405, {'error': 'Method not allowed.'})

    def do_POST(self):
        if not self._local():
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if length <= 0 or length > 12 * 1024 * 1024:
                self._send_json(413, {'error': 'Request is empty or too large.'})
                return
            if self.headers.get_content_type() != 'application/json':
                self._send_json(415, {'error': 'JSON is required.'})
                return
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError('A JSON object is required.')
            parts = urlsplit(self.path).path.strip('/').split('/')
            if parts == ['api', 'cases']:
                result = SERVICE.create(payload)
            elif len(parts) == 4 and parts[:2] == ['api', 'cases']:
                case_id, action = parts[2:]
                if action == 'evidence':
                    result = SERVICE.evidence(case_id, payload)
                elif action == 'review':
                    result = SERVICE.review(case_id, payload)
                elif action == 'confirm':
                    result = SERVICE.confirm(case_id)
                else:
                    self._send_json(404, {'error': 'Not found.'})
                    return
            else:
                self._send_json(404, {'error': 'Not found.'})
                return
            self._send_json(200, result)
        except FileNotFoundError:
            self._send_json(404, {'error': 'Application or required local data not found.'})
        except (KeyError, TypeError, ValueError) as error:
            self._send_json(400, {'error': str(error)})
        except Exception:
            import traceback
            traceback.print_exc()
            self._send_json(500, {'error': 'Processing failed. Check the server terminal and model availability, then retry. No result was fabricated.'})


def run_evidence_case(payload):
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
    member1 = Member1Output(
        case_id=case_id,
        product=detected_product,
        claimed_defect=damage_type,
        claimed_location=payload.get("damage_location", "left sleeve"),
        image_quality=float(payload.get("image_quality", 0.90)),
        blur_score=0.10,
        lighting_score=0.91,
        relevant_region_visible=image_usable,
        image_usable=image_usable,
    )
    member2 = Member2Output(
        case_id=case_id,
        detected_product=detected_product,
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
    import os
    os.chdir(PROJECT_ROOT)
    address = ("127.0.0.1", 8765)
    print("Risk-Aware Refund App: http://127.0.0.1:8765")
    ThreadingHTTPServer(address, RefundAppHandler).serve_forever()


if __name__ == "__main__":
    main()
