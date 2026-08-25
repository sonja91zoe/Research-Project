# Student 4 Week 5 Rule-Based Baseline

## Deliverables

- A normalized `EvidenceFeatures` schema that coexists with the existing
  Member 1-4 interfaces.
- An equally weighted evidence-confidence baseline using six confidence
  signals.
- Refund-risk classification using the existing low, medium, and high bands.
- A decision matrix with a policy-eligibility safeguard.
- A JSON adapter that runs `refund_001.json` through the baseline.
- Automated happy-path, safeguard, and input-validation tests.

## Confidence baseline

The prototype confidence score is the arithmetic mean of image quality,
damage confidence, claim-image consistency, image-order match, evidence
completeness, and policy match. All signals must be between 0 and 1.

## Decision rules

Policy-ineligible cases always require human review. Eligible cases use the
confidence/risk matrix in `src/decision/baseline.py`. For this Week 5
prototype, high-confidence refunds with low or medium financial risk may be
automatically refunded; high-risk refunds require human review.

## Mock result

`refund_001.json` produces evidence confidence `0.92` (`HIGH`), refund risk
`MEDIUM`, and decision `AUTO_REFUND`.
