# Student 4 Week 5: Rule-Based Confidence and Decision V1

## 1. Objective

The objective of Student 4 in Week 5 is to build a deterministic rule-based baseline for evidence confidence, refund risk, and refund decisions.

The module combines structured outputs from Members 1, 2, and 3 and produces one of three decisions:

- `AUTO_REFUND`
- `REQUEST_MORE_EVIDENCE`
- `HUMAN_REVIEW`

This Week 5 implementation is a transparent rule-based baseline. It is not the Week 6 machine-learning confidence model.

## 2. Inputs from Members 1-3

### Member 1: Claim and Image Quality

The following Member 1 fields are used:

- `image_quality`
- `relevant_region_visible`
- `image_usable`

### Member 2: Damage Detection and Visual Evidence

The following Member 2 fields are used:

- `damage_detected`
- `damage_confidence`
- `claim_image_consistency`

### Member 3: Order, Policy, and Evidence Verification

The following Member 3 fields are used:

- `order_valid`
- `image_order_consistency`
- `policy_eligible`
- `policy_match_score`
- `evidence_completeness`
- `refund_amount`

All three member outputs must contain the same `case_id`. The Agent raises an error if their case IDs are different.

## 3. Evidence Confidence

The evidence-confidence score is a weighted combination of six evidence features.

| Feature | Source | Weight |
|---|---|---:|
| `image_quality` | Member 1 | 0.15 |
| `damage_confidence` | Member 2 | 0.20 |
| `claim_image_consistency` | Member 2 | 0.20 |
| `image_order_consistency` | Member 3 | 0.15 |
| `policy_match_score` | Member 3 | 0.15 |
| `evidence_completeness` | Member 3 | 0.15 |

The weights sum to `1.00`.

The rule-based formula is:

```text
evidence_confidence =
    image_quality * 0.15
    + damage_confidence * 0.20
    + claim_image_consistency * 0.20
    + image_order_consistency * 0.15
    + policy_match_score * 0.15
    + evidence_completeness * 0.15
```

Damage confidence and claim-image consistency receive slightly higher weights because visible damage and support for the customer's claim are central to the refund decision.

Every evidence score must be between `0.00` and `1.00`. The module raises a `ValueError` when it receives an invalid score.

## 4. Confidence Labels

The numeric evidence-confidence score is converted into one of three labels.

| Score | Label |
|---:|---|
| `0.80` to `1.00` | `HIGH` |
| `0.50` to below `0.80` | `MEDIUM` |
| Below `0.50` | `LOW` |

These are manually defined prototype thresholds for the Week 5 baseline.

## 5. Refund Risk

Refund risk is based on the requested refund amount.

| Refund Amount | Risk |
|---:|---|
| `0` to `50` | `LOW` |
| Above `50` to `200` | `MEDIUM` |
| Above `200` | `HIGH` |

A negative refund amount is invalid and causes the module to raise a `ValueError`.

The refund-risk label describes financial exposure. It is not a predicted probability of fraud.

## 6. Override Rules

Override rules are evaluated before the confidence-risk decision matrix.

The rules are checked in the following order:

1. If `image_usable` is false, return `REQUEST_MORE_EVIDENCE`.
2. If `relevant_region_visible` is false, return `REQUEST_MORE_EVIDENCE`.
3. If `order_valid` is false, return `HUMAN_REVIEW`.
4. If `policy_eligible` is false, return `HUMAN_REVIEW`.
5. If `damage_detected` is false, return `REQUEST_MORE_EVIDENCE`.
6. If `claim_image_consistency` is below `0.50`, return `REQUEST_MORE_EVIDENCE`.

The override rules prevent a high average confidence score from hiding a critical problem such as an invalid order or unusable image.

## 7. Decision Matrix

If no override rule is triggered, the Agent uses the following decision matrix.

| Confidence | Refund Risk | Decision |
|---|---|---|
| `HIGH` | `LOW` | `AUTO_REFUND` |
| `HIGH` | `MEDIUM` | `HUMAN_REVIEW` |
| `HIGH` | `HIGH` | `HUMAN_REVIEW` |
| `MEDIUM` | `LOW` | `REQUEST_MORE_EVIDENCE` |
| `MEDIUM` | `MEDIUM` | `HUMAN_REVIEW` |
| `MEDIUM` | `HIGH` | `HUMAN_REVIEW` |
| `LOW` | `LOW` | `REQUEST_MORE_EVIDENCE` |
| `LOW` | `MEDIUM` | `REQUEST_MORE_EVIDENCE` |
| `LOW` | `HIGH` | `HUMAN_REVIEW` |

Automatic refund is only permitted when evidence confidence is `HIGH` and refund risk is `LOW`.

## 8. Agent Workflow

The Student 4 Agent performs the following steps:

1. Validate that Members 1-3 have the same `case_id`.
2. Calculate the weighted evidence-confidence score.
3. Convert the score into a confidence label.
4. Calculate the refund-risk band.
5. Apply the override rules.
6. Apply the decision matrix when no override rule is triggered.
7. Return a structured `Member4Output`.

The final output contains:

- `case_id`
- `evidence_confidence`
- `refund_risk`
- `decision`
- `reason`

## 9. Demonstration Case

The demonstration uses:

```text
data/test_cases/student4_auto_refund.json
```

The case contains usable image evidence, detected damage, consistent claim evidence, a valid order, confirmed policy eligibility, and a low refund amount.

The expected result is:

```json
{
  "case_id": "REFUND_001",
  "evidence_confidence": 0.92,
  "refund_risk": "LOW",
  "decision": "AUTO_REFUND",
  "reason": "Decision matrix result: confidence=HIGH, refund risk=LOW."
}
```

Run the demonstration from the project root:

```bash
python3 student4_demo.py
```

## 10. Testing

The Week 5 tests cover:

- Confidence weights summing to `1.00`
- Confidence-label boundaries
- Refund-risk boundaries
- Negative refund amounts
- Unusable images
- Hidden relevant product regions
- Invalid orders
- Ineligible refund policies
- Missing detected damage
- Low claim-image consistency
- Mismatched case IDs
- Invalid evidence scores

Run all tests from the project root:

```bash
python3 -m pytest -q
```

At the end of Week 5, the project test result is:

```text
23 passed
```

## 11. Week 5 Deliverables

Student 4 Week 5 delivers:

- Rule-based evidence-confidence calculation
- Confidence labels
- Refund-risk classification
- Override rules
- Confidence-risk decision matrix
- Integrated Student 4 Agent
- Demonstration program
- Boundary and failure-case tests
- Week 5 technical documentation

## 12. Limitations

The current confidence weights and thresholds are manually defined.

The evidence-confidence score is an interpretable rule-based score, not a calibrated probability.

The refund-risk classification only considers the refund amount. It does not currently include customer history, fraud indicators, product category, or uncertainty estimates.

The demonstration uses mock structured outputs rather than fully integrated live outputs from Members 1-3.

## 13. Week 6 Plan

In Week 6, Student 4 will:

- Build Logistic Regression and Random Forest confidence models.
- Compare ML models with the Week 5 rule-based baseline.
- Evaluate accuracy, precision, recall, F1 score, and confusion matrices.
- Analyse feature importance.
- Record failure cases.
- Evaluate and adjust decision thresholds.
- Preserve the Week 5 rule-based method as the baseline comparison.