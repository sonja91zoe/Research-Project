# Member 2 — Week 3 / member2-week6

Owner: Hangyi Zhang. This additive module consumes Week2 visual output and
Member1's extracted defect. It fills the existing `claim_image_consistency`
field without changing `src/common/schemas.py` or another member's code.

## Run from the repository root

```powershell
python -m pip install "pydantic>=2,<3" pytest
python -m pytest tests/test_member2_week3.py -q
python -m src.damage_detection.week3_demo data/member2/week3/refund_001.json
python -m src.damage_detection.prepare_week3 data/Week4_damage_dataset_v1/damage_dataset_v1.csv data/member2/week3
```

The JSON demo uses synthetic upstream predictions, not image inference. For real
images, call the existing Week2 detector, then pass its `Member2Output` to
`verify_claim(case, member1, member2)`. Pass the resulting Member2 output to the
team workflow as before. The separate `recommend_handoff` function is an advisory
integration example, not a modification of Member4 or an action that issues money.
Upstream order, policy, image/order and completeness checks must be supplied
explicitly in `HandoffContext`; no risk estimator is fabricated here.

## Rules

| Evidence | Verdict / consistency | Advisory route |
|---|---|---|
| Good evidence, supported defect type matches | positive / 1.0 | Auto Refund only with all upstream checks true and risk <= 0.20 |
| Good evidence, concrete defect type differs | negative / 0.0 | Manual Review |
| Missing/poor image, low confidence, unsupported claim | ambiguous / null | Request Evidence |
| Risk > 0.20 or failed order/policy/image-order check | any | Manual Review, overriding evidence requests |
| Missing upstream checks | positive | Manual Review |

The consistency values are categorical rule scores, not calibrated probabilities,
condition severity, or measurements of how much damage exists. The inherited 0.70
visual review threshold and illustrative 0.20 risk limit are configurable and are
not validated refund policy thresholds. Existing visual review flags are retained.
The module does not classify `no_damage` as verified: independent clean controls
are still absent. Product/location assertions and unsupported extracted defect
phrases abstain. Free-form natural language extraction remains Member1's contract;
this module does not treat arbitrary text keyword matches as semantic proof.

## Data and limitations

The review manifest retains every original Week1 column, adds normalized damage
labels, groups rows by `source_image_id`, and deterministically selects 20 source
images (29 cases) for review. `none` maps to `no_damage` only as a vocabulary mapping;
this is not endorsement of its provisional visual label. `uncertain_*` maps to
`uncertain`, preserving the original field for traceability.

All 100 cases remain ineligible for benchmarking pending independent annotation
review. Twenty clean-appearing cases conflict with the positive-defect source pool;
30 ambiguous cases require their actual derivative images to be created and
verified. Neither an absent derivative nor an original image is silently substituted
as ambiguous-image evidence. Review batches are not fresh train/test partitions:
the 70 images have already been used for model evaluation and threshold selection.
Do not claim independent test accuracy from this set. Dataset attribution remains
CISUTAC project — Wargön Innovation, as recorded in the original source documents.
