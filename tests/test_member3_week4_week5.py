import json

from src.evidence.order import load_orders, retrieve_order
from src.evidence.rag import retrieve_best_policy, retrieve_policies
from src.evidence.verification import verify_case


def load_cases():
    with open("data/test_cases/member3_cases.json", encoding="utf-8") as case_file:
        return json.load(case_file)


def test_week4_has_twelve_orders_and_cases():
    assert len(load_orders()) == 12
    assert len(load_cases()) == 12


def test_order_retrieval_is_case_insensitive():
    order = retrieve_order("ord001")
    assert order is not None
    assert order.product_name == "Black Jacket"
    assert order.price == 129.0


def test_unknown_order_returns_none():
    assert retrieve_order("ORD999") is None


def test_policy_retrieval_returns_ranked_traceable_results():
    policies = retrieve_policies("black jacket sleeve tear damage", top_k=2)
    assert policies[0].policy_id == "POL-DAMAGE-30"
    assert policies[0].policy_match >= policies[1].policy_match
    assert policies[0].policy_source


def test_wrong_item_query_retrieves_wrong_item_policy():
    policy = retrieve_best_policy("wrong incorrect item order mismatch")
    assert policy.policy_id == "POL-WRONG-ITEM-14"


def test_all_mock_cases_match_expected_eligibility():
    for case in load_cases():
        result = verify_case(case)
        assert result.policy_eligible is case["expected_eligible"], case["case_id"]
        assert 0.0 <= result.image_order_match <= 1.0
        assert 0.0 <= result.policy_match <= 1.0
        assert 0.0 <= result.evidence_completeness <= 1.0


def test_verified_case_is_traceable():
    result = verify_case(load_cases()[0])
    assert result.order_valid is True
    assert result.image_order_match == 1.0
    assert result.policy_eligible is True
    assert result.refund_amount == 129.0
    assert result.policy_source == "Mock Refund Policy, section 3.2"
