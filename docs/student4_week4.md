# Student 4 Week 4 Decision Framework

## 1. Feature Schema

Student 4 receives structured results from Members 1, 2, and 3.

### Member 1: Claim and image-quality features

- image_quality
- blur_score
- lighting_score
- relevant_region_visible
- image_usable

### Member 2: Damage and visual-evidence features

- damage_detected
- damage_type
- damage_confidence
- claim_image_consistency

### Member 3: Order, policy, and evidence features

- order_valid
- image_order_consistency
- policy_eligible
- policy_match_score
- evidence_completeness
- refund_amount

## 2. Evidence Confidence Labels

| Score | Label |
|---|---|
| 0.80 to 1.00 | HIGH |
| 0.50 to below 0.80 | MEDIUM |
| Below 0.50 | LOW |

These are prototype thresholds for Week 4. They may be evaluated and changed later.

## 3. Refund Risk Bands

| Refund amount | Risk |
|---|---|
| 0 to 50 | LOW |
| Above 50 to 200 | MEDIUM |
| Above 200 | HIGH |

The bands describe the financial risk of issuing a refund.
They do not issue or transfer money.

## 4. Decision Matrix

| Confidence | Risk | Decision |
|---|---|---|
| HIGH | LOW | AUTO_REFUND |
| HIGH | MEDIUM | HUMAN_REVIEW |
| HIGH | HIGH | HUMAN_REVIEW |
| MEDIUM | LOW | REQUEST_MORE_EVIDENCE |
| MEDIUM | MEDIUM | HUMAN_REVIEW |
| MEDIUM | HIGH | HUMAN_REVIEW |
| LOW | LOW | REQUEST_MORE_EVIDENCE |
| LOW | MEDIUM | REQUEST_MORE_EVIDENCE |
| LOW | HIGH | HUMAN_REVIEW |

## 5. Override Rules

Rules checked before the matrix:

1. If image_usable is false, request more evidence.
2. If relevant_region_visible is false, request more evidence.
3. If order_valid is false, send to human review.
4. If policy_eligible is false, send to human review.
5. If damage is not detected, request more evidence.
6. If claim_image_consistency is below 0.50, request more evidence.

## 6. Agent Output

The Agent returns:

- case_id
- evidence_confidence
- refund_risk
- decision
- reason

Possible decisions:

- AUTO_REFUND
- REQUEST_MORE_EVIDENCE
- HUMAN_REVIEW