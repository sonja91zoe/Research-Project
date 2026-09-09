# Damage Dataset V1

Week 1 deliverable for Hangyi Zhang's **Damage Detection + Visual Verification** module.

## Contents

- `damage_dataset_v1.csv`: 100 structured claim–image cases.
- `label_definitions.md`: operational labels and decision rules.
- `dataset_sources.md`: source pools, sampling, and provenance limitations.

## Dataset composition

| Verdict | Count | Composition |
|---|---:|---|
| Positive | 40 | 20 hole/tear + 20 stain/spot |
| Negative | 30 | 10 clean/false-hole + 10 clean/false-stain + 5 actual-hole/false-stain + 5 actual-stain/false-hole |
| Ambiguous | 30 | 15 uncertain hole/tear + 15 uncertain stain/spot |

The 100 cases cover all 70 unique source images. Additional rows are intentionally constructed through altered claims or ambiguous variants, and this is explicit in `case_origin`, `construction_method`, and `image_variant_id`.

## Recommended use

Use each row as one visual-verification task: provide the referenced image/variant and `claim_text`, then compare the module output with `expected_verdict` and `damage_type`. Treat `ambiguous` as a first-class outcome that triggers another-photo or human-review handling.

## Leakage control

Never randomly split rows. Group by `source_image_id` and place all claims and variants derived from the same photograph in the same partition.

## Reproducing ambiguous variants

Generate only the recipe named in `construction_method` from the original source image. Keep the source photograph unchanged, save the derivative separately using `image_variant_id`, and record the transformation parameters in a later manifest.

## Quality status

All labels are marked `provisional_week1`. Before benchmark or production use, perform a second human review of the 70 source photographs, recover upstream license/URL metadata, materialize the 30 ambiguous variants, and update confidence/review status.
