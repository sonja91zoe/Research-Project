import json
from src.common.schemas import (
    CaseInput,
    Member1Output,
    Member2Output,
    Member3Output,
    Member4Output
)
# 读取测试 JSON
with open(
    "data/test_cases/refund_001.json",
    "r",
    encoding="utf-8"
) as file:
    raw_data = json.load(file)


# 用我们定义的 CaseInput 验证数据
case = CaseInput(**raw_data)


print("Case loaded successfully!")
print(case)
from src.common.schemas import Member1Output


member1_result = Member1Output(
    case_id="REFUND_001",
    product="jacket",
    claimed_defect="tear",
    claimed_location="left_sleeve",
    image_quality=0.86,
    blur_score=0.12,
    lighting_score=0.91,
    relevant_region_visible=True,
    image_usable=True
)

print("\nMember 1 output loaded successfully!")
print(member1_result)
member2_result = Member2Output(
    case_id="REFUND_001",
    detected_product="black_jacket",
    damage_detected=True,
    damage_type="tear_hole",
    damage_location="left_sleeve",
    damage_confidence=0.92,
    claim_image_consistency=0.95
)

print("\nMember 2 output loaded successfully!")
print(member2_result)


member3_result = Member3Output(
    case_id="REFUND_001",
    order_valid=True,
    image_order_consistency=0.91,
    policy_eligible=True,
    policy_match_score=0.94,
    evidence_completeness=0.90,
    refund_amount=129.0,
    policy_source="Damaged Goods Policy Section 3.2"
)

print("\nMember 3 output loaded successfully!")
print(member3_result)


member4_result = Member4Output(
    case_id="REFUND_001",
    evidence_confidence=0.90,
    refund_risk="medium",
    decision="auto_refund",
    reason="Evidence is complete and consistent and the refund risk is acceptable."
)

print("\nMember 4 output loaded successfully!")
print(member4_result)