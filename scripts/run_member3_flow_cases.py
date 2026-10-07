"""Run six independent Member 3 flow checks without other members' models."""

import json
import sys
from dataclasses import asdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.evidence.order import retrieve_order
from src.evidence.rag import retrieve_best_policy
from src.evidence.verification import verify_case


CASES = PROJECT_ROOT / "data/test_cases/member3_manual_flow_cases.json"


def main() -> None:
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    passed = 0

    for case in cases:
        result = verify_case(case)
        order = retrieve_order(case["order_id"])
        policy = None
        if order is not None:
            policy = retrieve_best_policy(
                " ".join(
                    [order.product_category, case["damage_type"], case["claim_text"]]
                ),
                retailer=order.retailer,
            )

        correct = (
            result.policy_eligible is case["expected_eligible"]
            and result.reason == case["expected_reason"]
        )
        passed += int(correct)
        print(f"\n{case['case_id']} — {case['scenario']} — {'PASS' if correct else 'FAIL'}")
        print("Order:", asdict(order) if order else "NOT FOUND")
        print("Policy:", asdict(policy) if policy else "NOT RETRIEVED")
        print("Output:", asdict(result))

    print(f"\nRESULT: {passed}/{len(cases)} flow cases passed")
    if passed != len(cases):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
