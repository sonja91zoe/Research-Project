import json
from pathlib import Path
import pytest
from src.agent.final_agent import run_final_agent
from src.common.schemas import Member1Output, Member2Output, Member3Output

ROOT = Path(__file__).resolve().parents[1]

def evidence(score):
    case = json.loads((ROOT / 'data/member4/week8/validation_inputs.json').read_text())[0]
    return (Member1Output(**{**case['member1'], 'image_quality': score}),
            Member2Output(**{**case['member2'], 'damage_confidence': score, 'claim_image_consistency': score}),
            Member3Output(**{**case['member3'], 'image_order_match_status': 'MATCH', 'image_order_consistency': score, 'policy_match_score': score, 'evidence_completeness': score}))

@pytest.mark.parametrize('ml_score,rule_score,expected', [(0.89,0.95,'REQUEST_MORE_EVIDENCE'), (0.97,0.79,'REQUEST_MORE_EVIDENCE'), (0.90,0.80,'AUTO_REFUND')])
def test_ml_auto_requires_both_thresholds(monkeypatch, ml_score, rule_score, expected):
    monkeypatch.setattr('src.decision.ml_confidence.predict_evidence_confidence', lambda *a, **k: ml_score)
    assert run_final_agent(*evidence(rule_score), confidence_method='ml').decision == expected

def test_guard_does_not_bypass_policy_or_review(monkeypatch):
    monkeypatch.setattr('src.decision.ml_confidence.predict_evidence_confidence', lambda *a, **k: 0.99)
    m1, m2, m3 = evidence(0.95)
    assert run_final_agent(m1, m2, m3.model_copy(update={'policy_eligible': False}), confidence_method='ml').decision == 'HUMAN_REVIEW'
    assert run_final_agent(m1.model_copy(update={'image_usable': False}), m2, m3, confidence_method='ml').decision == 'REQUEST_MORE_EVIDENCE'
    assert run_final_agent(m1, m2.model_copy(update={'needs_human_review': True}), m3, confidence_method='ml').decision == 'HUMAN_REVIEW'
