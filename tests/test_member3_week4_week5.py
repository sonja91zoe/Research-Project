import json

from src.evidence.order import load_orders, retrieve_order
from src.evidence.rag import retrieve_best_policy, retrieve_policies
from src.evidence.verification import verify_case


def load_cases():
    with open("data/test_cases/member3_cases.json", encoding="utf-8") as case_file:
        return json.load(case_file)


def test_order_database_has_seventy_traceable_records_and_twelve_legacy_cases():
    assert len(load_orders()) == 70
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


def test_official_multi_retailer_policy_sources_are_selectable():
    zara = retrieve_best_policy("defective jacket hole", retailer="Zara Australia")
    uniqlo = retrieve_best_policy("faulty shirt stain", retailer="UNIQLO Australia")

    assert zara.policy_id == "ZARA-AU-DAMAGE-30"
    assert zara.source_url == "https://www.zara.com/au/en/help-center/HowToReturn"
    assert uniqlo.policy_id == "UNIQLO-AU-DAMAGE-30"
    assert uniqlo.source_url.startswith("https://faq-au.uniqlo.com/")


def test_all_mock_cases_reflect_current_eligibility():
    for case in load_cases():
        result = verify_case(case)
        # M3_009's legacy "Grey Hoodie" prediction is a full product name.
        # It no longer establishes a supported category mismatch with Jacket.
        if case["case_id"] == "M3_009":
            assert result.image_order_match_status == "NOT_AVAILABLE"
            assert result.policy_eligible is True
            explicit_category_case = {**case, "detected_product": "hoodie"}
            mismatch = verify_case(explicit_category_case)
            assert mismatch.image_order_match_status == "MISMATCH"
            assert mismatch.policy_eligible is False
        else:
            assert result.policy_eligible is case["expected_eligible"], case["case_id"]
        assert 0.0 <= result.image_order_match <= 1.0
        assert 0.0 <= result.policy_match <= 1.0
        assert 0.0 <= result.evidence_completeness <= 1.0


def test_verified_case_is_traceable():
    result = verify_case(load_cases()[0])
    assert result.order_valid is True
    # The legacy case supplies a product name, not a supported category label.
    assert result.image_order_match == 0.5
    assert result.image_order_match_status == "NOT_AVAILABLE"
    assert result.policy_eligible is True
    assert result.refund_amount == 129.0
    assert result.policy_source == (
        "H&M Australia Terms and Conditions, sections 5, 6 and 10"
    )
    assert "hm.com" in retrieve_best_policy("jacket damage").source_url
