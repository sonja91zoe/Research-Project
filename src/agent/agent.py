"""Student 4 Week 5 rule-based confidence and decision Agent."""

from src.common.schemas import (
    Member1Output,
    Member2Output,
    Member3Output,
    Member4Output,
)
from src.decision.confidence import (
    calculate_evidence_confidence,
    get_confidence_label,
)
from src.decision.decision import make_decision
from src.decision.risk import calculate_refund_risk


def run_agent(
    member1: Member1Output,
    member2: Member2Output,
    member3: Member3Output,
) -> Member4Output:
    """Combine Members 1–3 outputs into the final refund decision."""

    case_ids = {
        member1.case_id,
        member2.case_id,
        member3.case_id,
    }

    if len(case_ids) != 1:
        raise ValueError(
            "Member outputs have different case_id values."
        )

    evidence_confidence = calculate_evidence_confidence(
        member1,
        member2,
        member3,
    )

    confidence_label = get_confidence_label(
        evidence_confidence
    )

    refund_risk = calculate_refund_risk(
        member3.refund_amount
    )

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