# Member 2 — Week 2 Damage Detection V1

Owner: Hangyi Zhang

## Scope

This module performs **garment image → visible damage classification**. It preserves the Week 1 labels:

- `hole_or_tear`
- `stain_or_spot`
- `no_damage`
- `uncertain` when evidence quality is insufficient

Claim–image consistency remains optional in the shared schema and is not calculated in Week 2; it belongs to Week 3.

## Safety behaviour

Images marked `poor` or `unusable` bypass automatic classification and are routed to human review. Predictions below the default confidence threshold of `0.70` are also reviewed.

## Automated testing

GitHub Actions runs `python -m unittest tests.test_member2_damage -v` on every push to `student2-week5` and on relevant pull requests. The tests cover shared-schema integration, concrete damage, poor evidence, low confidence, invalid state, and missing files.

The separate `Week 2 CLIP evaluation` workflow is manual. It downloads
`openai/clip-vit-base-patch32`, reads the committed Week 1 images, and uploads
`week2_predictions.csv` and `week2_metrics.json` as workflow artifacts. It uses
no paid model API and needs no API key.

## Current evaluation status

The local Week 1 collection has been audited: all 70 expected JPEG files are
present and readable. Sixty source photos currently have explicit image-only
ground truth in the Week 1 manifest (25 `hole_or_tear`, 20 `stain_or_spot`, and
15 `no_damage`). The remaining 10 source photos occur only in recipes for
ambiguous derived variants, so they are excluded until those variants are
materialized or the original photos receive a second human label. This is a
data-integrity result, not model accuracy; no result is fabricated from folder
or filename labels.

The source datasets are Wargön Innovation's `Garment_condition_holes` and
`Garment_condition_spots`, both published under CC BY 4.0. Attribution and
links are recorded in `data/member2/week1/README.md`.
