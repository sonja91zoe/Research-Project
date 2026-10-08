import base64
from pathlib import Path
import pytest
from cloud_pilot.core import Runtime
from cloud_pilot.workflow import SessionRefundService

ROOT = Path(__file__).resolve().parents[1]

def payload():
    return {'order_id': 'ORD001', 'request_date': '2026-08-15',
            'claim_text': 'The jacket has a tear on the left sleeve.',
            'image_base64': base64.b64encode((ROOT / 'data/member1/images/member1_jacket_001.jpg').read_bytes()).decode(),
            'relevant_region_visible': True}

def test_isolation_review_and_idempotence():
    paths = []
    def pipeline(case, **kwargs):
        paths.append(Path(case.image_paths[0]))
        assert paths[-1].exists()
        assert kwargs['confidence_method'] == 'rule'
        return {'decision': {'decision': 'HUMAN_REVIEW', 'reason': 'Missing evidence'}}
    runtime = Runtime(detector=object())
    a, b = SessionRefundService(runtime, pipeline), SessionRefundService(runtime, pipeline)
    record = a.create(payload())
    key = record['case_id']
    assert not paths[-1].exists()
    assert b.list() == []
    with pytest.raises(ValueError):
        b.get(key)
    with pytest.raises(ValueError):
        a.confirm(key)
    reviewed = a.review(key, {'action': 'APPROVE', 'reviewer': 'Demo', 'note': 'Workflow only'})
    assert reviewed['assessments'] == record['assessments']
    done = a.confirm(key)
    assert a.confirm(key) == done
    assert len(done['events']) == 3

def test_reassessment_and_failure_preserve_record():
    fail = False
    def pipeline(case, **kwargs):
        if fail:
            raise RuntimeError('Model unavailable')
        return {'decision': {'decision': 'REQUEST_MORE_EVIDENCE'}}
    runtime = Runtime(detector=object())
    service = SessionRefundService(runtime, pipeline)
    record = service.create(payload())
    key = record['case_id']
    record = service.evidence(key, payload())
    assert len(record['assessments']) == 2
    fail = True
    with pytest.raises(RuntimeError):
        service.evidence(key, payload())
    assert service.get(key) == record
    assert not runtime.lock.locked()

def test_real_chain_keeps_missing_visual_evidence():
    from src.damage_detection.damage import DamageDetector, DamagePrediction

    class Backend:
        def predict(self, image_path):
            return DamagePrediction(
                damage_type="stain_or_spot",
                confidence=0.9,
                rationale="Controlled test",
            )

    service = SessionRefundService(
        Runtime(detector=DamageDetector(backend=Backend()))
    )
    record = service.create(payload())
    result = record["assessments"][0]["result"]

    assert result["member2"]["claim_image_consistency"] == 0.0
    assert "claim_image_consistency" not in result["missing_evidence"]
    assert "detected_product" in result["missing_evidence"]
    assert "damage_location" in result["missing_evidence"]
    assert result["member3"]["policy_eligible"] is False
    assert record["status"] == "PENDING_REVIEW"


def test_order_source_is_forwarded_to_the_pipeline(tmp_path):
    received = []

    def pipeline(case, **kwargs):
        received.append(kwargs['order_source'])
        return {'decision': {'decision': 'HUMAN_REVIEW'}}

    source = tmp_path / 'orders.db'
    service = SessionRefundService(
        Runtime(detector=object()), pipeline, order_source=source
    )
    service.create(payload())
    assert received == [source]
