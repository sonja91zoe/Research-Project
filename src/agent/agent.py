"""Week 4 mock workflow Agent for Student 4."""

from src.common.schemas import Member4Output
from src.decision.confidence import (
    calculate_evidence_confidence,
    get_confidence_label,
)
from src.decision.risk import calculate_refund_risk
from src.decision.decision import make_decision


def run_agent(member1, member2, member3):
    """Combine mock outputs from Members 1-3 and return Member4Output."""

    case_ids = {
        member1.case_id,
        member2.case_id,
        member3.case_id,
    }

    if len(case_ids) != 1:
        raise ValueError("Member outputs have different case_id values.")

    evidence_confidence = calculate_evidence_confidence(
        member1,
        member2,
        member3,
    )
    confidence_label = get_confidence_label(evidence_confidence)
    refund_risk = calculate_refund_risk(member3.refund_amount)

    decision, reason = make_decision(
        confidence_label,
        refund_risk,
        member1,
        member2,
        member3,
    )

    return Member4Output(
        case_id=member1.case_id,
        evidence_confidence=evidence_confidence,
        refund_risk=refund_risk,
        decision=decision,
        reason=reason,
    )
