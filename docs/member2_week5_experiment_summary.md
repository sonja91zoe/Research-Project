# Member 2 — Week 5 visual-evidence experiments

Owner: Hangyi Zhang

## What this evaluates

`scripts/member2_week5_evaluate.py` joins the Week 1 100-case manifest to the
existing Member 2 damage detector and Claim–Image Verification module. It writes
one row per case to `data/member2/week5/week5_results.csv`, then calculates
damage and claim-consistency Accuracy, macro Precision, Recall, and F1 from
**executed** predictions only. When predictions exist, it also writes two PNG
confusion matrices.

The runner uses the actual visual state for damage ground truth (`none` maps to
`no_damage`) and the Week 1 `expected_verdict` for claim consistency. Thus a
wrong claim can be evaluated independently from whether a defect is visible.

## Leakage control

The unit of independence is `source_image_id`, not case id or filename. Any
future train/test split must place all cases and derivatives of a source image
in the same partition. The result CSV retains this key specifically for audit.

## Current asset limitation

The manifest has 100 cases but only 70 materialized original JPEGs. The 30
ambiguous cases (mild blur, partial occlusion, tight crop, reduced contrast,
and incomplete view) are recipes only, not separate image files. They are
reported as `not_materialized_variant`; no prediction, metric, or confusion
matrix cell is fabricated for them. The original 70 also contain provisional
clean-appearing controls, so any `no_damage` metric must be labelled
provisional until independently sourced clean controls are added.

## Recorded CLIP baseline

The committed Week 5 run uses the cached `openai/clip-vit-base-patch32` model
and executes the 70 materialized source-image cases. It does not make a claim
about the 30 unmaterialized ambiguous variants. The exact outputs, including
the two confusion matrices and failure-review queue, are in
`data/member2/week5/`. The result must be interpreted as a zero-shot baseline:
the detector's hole/tear performance is poor, and the provisional clean controls
are not independently sourced.

| Evaluation | Executed cases | Accuracy | Macro F1 | Key result |
| --- | ---: | ---: | ---: | --- |
| Damage detection | 70 | 34.29% | 26.15% | Hole/tear recall: 0.00%; stain/spot recall: 80.00%; provisional no-damage recall: 20.00%. |
| Claim–image verification | 70 | 22.86% | 31.56% | Positive-claim recall: 25.00%; wrong-claim/negative recall: 20.00%. |

The run produced 58 failure or human-review rows; the first ten are listed in
`data/member2/week5/failure_cases.md`. These are observed model outcomes, not
hand-authored predictions.

## Run instructions

Preflight inventory (safe when no model weights/cache are available):

```text
python -m scripts.member2_week5_evaluate --backend none
```

Measured YOLO evaluation (use only the actual trained `best.pt` artifact):

```text
python -m scripts.member2_week5_evaluate --backend yolo --weights path/to/best.pt
```

CLIP can be selected with `--backend clip`; it requires the existing
Transformers model download/cache and should be recorded as a distinct baseline.

## Failure-case review

After a measured run, select up to ten rows where either predicted label differs
from its expected value or `needs_human_review` is true. Record the case id,
source image id, expected/predicted labels, confidence, and a visual explanation
in `data/member2/week5/failure_cases.md`. Do not infer a failure case from a
recipe-only variant.
