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

The completed second run evaluated all 70 images. Automatic-prediction accuracy
was 44.4% at 90.0% coverage, end-to-end accuracy was 40.0%, and macro F1 was
34.5%. `stain_or_spot` recall reached 77.1% (27/35), but `hole_or_tear` recall
was only 2.9% (1/35). The CLIP implementation is therefore retained as a
reproducible Week 2 baseline, not represented as a production-ready detector.
The committed machine-readable result and interpretation are in
`data/member2/week2/results/`.

The next image-model iteration should use a small pretrained object detector
trained with the recovered YOLO annotations. The same detector can remain the
visual component in later weeks; Week 3 should consume its output when checking
claim consistency rather than replacing the visual model. The 70 current images
should remain held out from detector training, and clean controls must be added
before making any `no_damage` performance claim.

The repository now includes a leakage-safe YOLO dataset builder, a YOLO backend
that produces the shared `Member2Output`, and a manually triggered
`Week 2 YOLO training` GitHub Actions workflow. It downloads the two public
source datasets, excludes every augmentation group related to the 70 held-out
images, remaps their separate class IDs to the shared two-class convention, and
uploads the trained weights and metrics as a temporary workflow artifact.
Training remains manual because it is substantially more expensive than unit
testing. Until clean controls are added, a run with no detected box is routed to
`uncertain` rather than asserted to be `no_damage`.

The first 10-epoch YOLO smoke run completed successfully but exposed mixed box
and polygon rows in the source labels. Its held-in validation performance was
not acceptable (recall 1.24%, mAP50 0.58%), so its weights are retained only as
a pipeline baseline. The dataset builder now converts every polygon to a
normalized bounding box before training. The next workflow run uses 20 epochs
at 512 pixels and automatically evaluates `best.pt` on the 70 held-out images.

The corrected 20-epoch model was subsequently calibrated at five inference
thresholds. A candidate threshold of 0.01 gave the best held-out balance:
68.6% `hole_or_tear` recall, 65.7% `stain_or_spot` recall, 72.3% macro F1, and
67.1% end-to-end accuracy. This threshold only surfaces possible damage. It
does not override the 0.70 human-review threshold, and it has not been validated
on `no_damage` controls. The complete comparison is recorded in
`data/member2/week2/results/yolo_threshold_comparison.json`.

The source datasets are Wargön Innovation's `Garment_condition_holes` and
`Garment_condition_spots`, both published under CC BY 4.0. Attribution and
links are recorded in `data/member2/week1/README.md`.

## Recovered annotation provenance

`data/member2/week2/source_file_mapping.csv` records the perceptual and pixel
match from each renamed image to its upstream filename. All 70 accepted matches
have pixel RMSE below 1.0 after normalization. Corresponding normalized YOLO
labels are stored in `data/member2/week2/labels/`; crops are generated during
evaluation and are not committed as duplicate image assets.
