"""End-to-end single-case evidence chain for Member 3 Week 6."""

from dataclasses import asdict

from src.common.schemas import CaseInput, Member1Output, Member2Output, Member3Output
from src.evidence.models import EvidenceChain
from src.evidence.order import retrieve_order
from src.evidence.rag import retrieve_best_policy
from src.evidence.verification import verify_case


def build_evidence_chain(
    case_input: CaseInput,
    member1: Member1Output,
    member2: Member2Output,
    request_date: str,
) -> EvidenceChain:
    """Build a traceable evidence chain and Member 3 output for one case."""

    case_ids = {case_input.case_id, member1.case_id, member2.case_id}
    if len(case_ids) != 1:
        raise ValueError("CaseInput and member outputs have different case_id values.")

    order = retrieve_order(case_input.order_id)
    detected_product = member2.detected_product or member1.product or ""
    verification_input = {
        "case_id": case_input.case_id,
        "order_id": case_input.order_id,
        "claim_text": case_input.claim_text,
        "image_present": bool(case_input.image_paths),
        "image_usable": member1.image_usable,
        "detected_product": detected_product,
        "damage_detected": member2.damage_detected,
        "damage_type": member2.damage_type,
        "claim_image_consistency": member2.claim_image_consistency,
        "request_date": request_date,
    }
    verified = verify_case(verification_input)

    policy = None
    if order is not None:
        policy = retrieve_best_policy(
            " ".join(
                [order.product_category, member2.damage_type, case_input.claim_text]
            )
        )

    member3 = Member3Output(
        case_id=case_input.case_id,
        order_valid=verified.order_valid,
        image_order_consistency=verified.image_order_match,
        policy_eligible=verified.policy_eligible,
        policy_match_score=verified.policy_match,
        evidence_completeness=verified.evidence_completeness,
        refund_amount=verified.refund_amount,
        policy_source=verified.policy_source,
    )

    return EvidenceChain(
        case_id=case_input.case_id,
        claim={
            "text": case_input.claim_text,
            "product": member1.product,
            "claimed_defect": member1.claimed_defect,
            "claimed_location": member1.claimed_location,
        },
        image_evidence={
            "paths": list(case_input.image_paths),
            "image_quality": member1.image_quality,
            "image_usable": member1.image_usable,
            "detected_product": member2.detected_product,
            "damage_detected": member2.damage_detected,
            "damage_type": member2.damage_type,
            "damage_location": member2.damage_location,
            "damage_confidence": member2.damage_confidence,
            "claim_image_consistency": member2.claim_image_consistency,
        },
        order_evidence=order,
        policy_evidence=policy,
        verified_evidence=verified,
        member3_output=member3.model_dump(),
    )


def evidence_chain_to_dict(chain: EvidenceChain) -> dict:
    """Serialize an evidence chain for logging, demos, or downstream agents."""

    return asdict(chain)
