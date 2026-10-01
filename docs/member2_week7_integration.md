# Member 2 — Week 7 Agent Integration

Owner: Hangyi Zhang

## Objective

Connect Member 1's parsed claim and image-usability output to the real Member 2
damage detector, calculate claim-image consistency, and expose the structured
visual evidence to the shared Agent pipeline.

## Integrated flow

The shared entry point is `src/agent/pipeline.py::run_pipeline`:

1. `run_member1` parses the claim and assesses image quality.
2. `run_member2_verification` runs the image detector.
3. `verify_claim` compares the claimed defect and optional location with the
   visual result.
4. The verified `Member2Output` is passed to Member 3 and Member 4 unchanged.
5. The pipeline returns both `member2` and an explanatory
   `member2_verification` object.

`run_member2` remains available and still returns `Member2Output`, so existing
callers do not need to change.

## Interface

Input contracts are the shared `CaseInput` and `Member1Output` models. Output
uses the existing `Member2Output` model. Claim-image consistency is:

- `1.0`: supported defect type and, when claimed, supported location.
- `0.0`: concrete visual evidence contradicts the claim.
- `null`: the evidence is insufficient for a reliable comparison.

These are categorical rule scores, not calibrated probabilities. Product-to-order
verification remains Member 3's responsibility. Member 2 does not substitute the
product parsed from customer text for a visually detected product.

## Evidence gates

Unusable images, hidden relevant regions, low-confidence predictions, unsupported
claim types, and missing visual location for a location-specific claim produce an
ambiguous result and require human review. A concrete mismatch produces a negative
result while preserving the detector's original review flag.

The current adapter accepts exactly one image. The default detector is the local
CLIP backend. A configured `DamageDetector` such as the YOLO-backed detector can be
injected through the existing `detector` argument.

## Validation

Run the integration tests from the repository root:

```bash
python -m pytest tests/test_member2_week7_integration.py tests/test_student4_week7_pipeline.py -q
```

Run the real CLIP demonstration:

```bash
python member2_week7_integration_demo.py
```

The demo may download `openai/clip-vit-base-patch32` on first use. It reports
missing product or location evidence instead of inventing it. The existing YOLO
weights are not committed to this repository and must be supplied separately if
the YOLO backend is selected.

## Recorded real-image smoke run

The default demo was run locally with
`data/member1/images/member1_jacket_001.jpg`. Member 1 marked the image usable.
CLIP predicted `stain_or_spot` with confidence `0.719`, while the demo claim
reported a tear. Member 2 therefore returned a `negative` verdict with
`claim_image_consistency=0.0`; the downstream Agent routed the case to
`HUMAN_REVIEW` because policy eligibility was not confirmed.

This run verifies that the real CLIP backend reaches the shared Agent and that a
visual contradiction is preserved. It is one smoke test and is not an accuracy
estimate. The detector still does not provide a visual product label for this
case, so `detected_product` remains missing and Member 3 assigns an image-order
consistency score of zero.
