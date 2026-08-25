"""Adapter from the normalized evidence-case JSON to the Week 5 baseline."""

import json
from pathlib import Path
from typing import Any

from src.common.schemas import EvidenceFeatures
from src.decision.baseline import BaselineDecision, make_baseline_decision


def evidence_features_from_case(case: dict[str, Any]) -> EvidenceFeatures:
    """Build normalized evidence features from a case dictionary."""

    return EvidenceFeatures(
        **case["evidence_features"],
        refund_amount=case["refund_amount"],
        order_id=case.get("order_id"),
        product_name=case.get("product_name"),
        product_category=case.get("product_category"),
    )


def run_evidence_case(case: dict[str, Any]) -> BaselineDecision:
    """Run the Week 5 baseline for one normalized evidence case."""

    return make_baseline_decision(evidence_features_from_case(case))


def load_and_run_evidence_case(filename: str | Path) -> BaselineDecision:
    """Load a JSON case and run the Week 5 baseline."""

    with Path(filename).open(encoding="utf-8") as case_file:
        return run_evidence_case(json.load(case_file))
