"""Week 7 single-image end-to-end Agent pipeline."""

from datetime import date

from src.agent.agent import run_agent
from src.agent.member1_adapter import run_member1
from src.agent.member2_adapter import run_member2_verification
from src.common.schemas import CaseInput, Member3Output
from src.evidence.pipeline import (
    build_evidence_chain,
    evidence_chain_to_dict,
)


def run_pipeline(
    case: CaseInput,
    *,
    request_date: str,
    relevant_region_visible: bool,
    confidence_method: str = "ml",
    detector=None,
    model=None,
) -> dict:
    """Run Members 1-3, confidence scoring, risk and decision.

    V1 supports exactly one image.
    Run from the project root because existing modules use
    project-relative model and data paths.
    """

    if confidence_method not in {"rule", "ml"}:
        raise ValueError(
            "confidence_method must be 'rule' or 'ml'."
        )

    date.fromisoformat(request_date)

    member1, raw_quality = run_member1(
        case,
        relevant_region_visible=relevant_region_visible,
    )

    member2_verification = run_member2_verification(
        case,
        member1,
        detector=detector,
    )
    member2 = member2_verification.member2

    chain = build_evidence_chain(
        case_input=case,
        member1=member1,
        member2=member2,
        request_date=request_date,
    )

    member3 = Member3Output(
        **chain.member3_output
    )

    decision = run_agent(
        member1,
        member2,
        member3,
        confidence_method=confidence_method,
        model=model,
    )

    missing_evidence = []

    if not member2.detected_product:
        missing_evidence.append("detected_product")

    if member2.claim_image_consistency is None:
        missing_evidence.append("claim_image_consistency")

    if (
        member1.claimed_location
        and not member2.damage_location
    ):
        missing_evidence.append("damage_location")

    return {
        "case_id": case.case_id,
        "request_date": request_date,
        "confidence_method": confidence_method,
        "member1": member1.model_dump(),
        "raw_image_quality": raw_quality,
        "member2": member2.model_dump(),
        "member2_verification": member2_verification.model_dump(
            exclude={"member2"}
        ),
        "member3": member3.model_dump(),
        "missing_evidence": missing_evidence,
        "evidence_chain": evidence_chain_to_dict(chain),
        "decision": decision.model_dump(),
    }
