# Damage Dataset V1 — Label Definitions

Owner: Hangyi Zhang  
Module: Damage Detection + Visual Verification  
Version: Week 1 / V1

## Case labels

### `positive`
The claim matches damage that is sufficiently visible in the image. V1 contains 20 `hole_or_tear` and 20 `stain_or_spot` positive cases.

### `negative`
The image does not support the stated claim. This includes a clean-appearing garment with a false damage claim and a real defect whose type differs from the claim. V1 contains 10 clean/false-hole, 10 clean/false-stain, 5 actual-hole/false-stain, and 5 actual-stain/false-hole cases.

### `ambiguous`
The image cannot support a reliable verdict because the relevant area is cropped, blurred, occluded, low-contrast, or incompletely shown. Ambiguous is not a weak positive or weak negative; it means request another image or escalate to human review. V1 contains 15 hole/tear and 15 stain/spot ambiguous cases.

## Damage types

- `hole_or_tear`: visible opening, ripped fabric, missing fabric, or seam/fabric tear.
- `stain_or_spot`: localized discoloration, mark, residue, or spot that is visibly distinct from normal fabric appearance.
- `none`: no clear defect visible for the case.
- `uncertain_hole_or_tear` / `uncertain_stain_or_spot`: the claim type is known but the image evidence is insufficient.

## Confidence

- `high`: defect/type match is visually clear in the Week 1 triage.
- `medium`: usable provisional judgment, but source image should be rechecked before benchmark release.
- `low`: intentionally insufficient evidence; normally paired with `ambiguous`.

## Decision rule

1. Identify the exact claim type.
2. Check whether the relevant garment area is visible at usable quality.
3. If evidence is insufficient, label `ambiguous`.
4. If sufficient, compare the visible defect type with the claim: matching is `positive`; absent or mismatched is `negative`.

## Important V1 limitation

These are 100 structured claim–image cases built from 70 unique source images. They are not 100 independent photographs. Rows sharing `source_image_id` must remain in the same train/validation/test group to prevent leakage.
