# Week 2 evaluation result

This folder records the reproducible GitHub Actions evaluation of the free,
local CLIP baseline. The test set contains 70 garment images: 35
`hole_or_tear` and 35 `stain_or_spot`.

## Result

- Automatic-prediction accuracy: 44.4% at 90.0% coverage
- End-to-end accuracy: 40.0%
- Macro F1: 34.5%
- `hole_or_tear` recall: 2.9% (1/35 correct)
- `stain_or_spot` recall: 77.1% (27/35 correct)
- Human-review/uncertain cases: 7/70

The run confirms that the pipeline and shared output schema work, but the
zero-shot CLIP baseline is strongly biased toward `stain_or_spot` and is not
accurate enough to be the final visual detector. These results must not be
reported as performance on `no_damage`, because this evaluation subset has no
clean controls.

`week2_metrics.json` contains the machine-readable result. Per-image
predictions remain downloadable from the corresponding GitHub Actions artifact
because they include runner-specific file paths and generated crop paths.

## Next model step

Retain this run as the Week 2 baseline. Train a small pretrained object detector
using the recovered YOLO annotations, keep the current 70 images as a held-out
evaluation set, and add independently sourced clean controls before evaluating
`no_damage`. Week 3 claim-image consistency is intentionally out of scope.
