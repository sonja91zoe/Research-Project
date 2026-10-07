# Member 1–4 final integration

## Implemented flow

1. Member 1 parses the English claim and checks whether the uploaded image is usable.
2. Member 2 uses the bundled YOLO weight to predict garment damage and an independent CLIP classifier to predict garment type.
3. Member 3 retrieves the order and policy, then reports `MATCH`, `MISMATCH`, or `NOT_AVAILABLE` for the photo/order comparison.
4. Member 4 combines the evidence into an automated refund, request-more-evidence, or human-review recommendation.

Dataset labels are evaluation ground truth only. They are not supplied to either image model, and order categories are not copied into image predictions.

## Verification results

- Automated regression tests: 161 passed after the final presentation and manifest tests were added.
- A new external image completed the full flow. Product classification returned `shirt` (score 0.817); YOLO returned `hole_or_tear` (score 0.552). The selected demo order was a jacket, so the comparison correctly returned `MISMATCH` and the case was routed to human review.
- The Week 4 manifest contains 100 cases but only 50 direct two-class cases (`hole_or_tear` and `stain_or_spot`). On those 50 in-scope cases, the bundled YOLO weight classified 33 correctly (66%).
- The remaining manifest cases include `none` and deliberately ambiguous labels that this two-class YOLO model was not trained to output. They must not be represented as two-class model successes.
- At the conservative 0.70 review threshold, no evaluated case qualifies for review-free automation. This is a measured limitation, not a fabricated success. Threshold reduction is not justified by the current evaluation because the lower-confidence subset does not achieve adequate selective accuracy.

## Current limits

- Product classification is zero-shot and needs a separately labelled garment-type validation set before its score can be described as calibrated accuracy.
- Damage location is not produced by the current two-class YOLO backend.
- Human review remains necessary when damage confidence is low, product identity is unavailable, the image and order mismatch, or required evidence is missing.
- Refund actions in the UI are simulated; no payment is sent.
