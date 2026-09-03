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
present and readable. The first CLIP run incorrectly reused claim-verification
fields as image-only ground truth. Original YOLO annotations were subsequently
recovered by matching the renamed JPEGs to the upstream datasets. The dedicated
Week 2 manifest now contains 35 `hole_or_tear` and 35 `stain_or_spot` images.
It does not claim to evaluate `no_damage`, because this positive-defect subset
contains no independently sourced clean controls.

The first whole-image run is retained as a baseline and data-pipeline finding.
The second evaluation uses prompt ensembles and combines each full image with a
YOLO-derived defect crop. End-to-end metrics count `uncertain` predictions as
misses for class recall while separately reporting selective accuracy and
coverage.

The source datasets are Wargön Innovation's `Garment_condition_holes` and
`Garment_condition_spots`, both published under CC BY 4.0. Attribution and
links are recorded in `data/member2/week1/README.md`.

## Recovered annotation provenance

`data/member2/week2/source_file_mapping.csv` records the perceptual and pixel
match from each renamed image to its upstream filename. All 70 accepted matches
have pixel RMSE below 1.0 after normalization. Corresponding normalized YOLO
labels are stored in `data/member2/week2/labels/`; crops are generated during
evaluation and are not committed as duplicate image assets.
