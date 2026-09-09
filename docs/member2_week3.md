# Member 2 Week 3 progress (working branch: member2-week6)

Owner: Hangyi Zhang. Prepared 2026-09-10. Status: uncommitted draft for user review.

## Verified prior work

- `Member2-week4/data/Week4_damage_dataset_v1`: downloaded and parsed the actual
  100-row CSV, containing 70 source IDs and 40 positive / 30 negative / 30 ambiguous
  cases. Its README and label definitions explicitly mark the labels provisional.
- `student2-week5/docs/member2_week2.md`: documents recovered annotations, the
  35-hole / 35-spot visual manifest, CLIP evaluation, leakage-safe YOLO training,
  polygon-to-box normalization and threshold comparison. Reported YOLO figures
  are 68.6% hole recall, 65.7% spot recall, 72.3% macro F1 and 67.1% end-to-end
  accuracy at candidate threshold 0.01. These are prior recorded results, not a
  new run. The 0.70 review threshold remains separate from candidate detection.
- `member2-week6` was inspected at base `ca951eaa55db15f9c07f6ed70f1b22e4391af235`.
  Its Member2 detector uses `src/common/schemas.py`, with an existing optional
  `claim_image_consistency` field. The original schema was downloaded unchanged
  for testing. No other member's implementation or branch was changed.

## Work prepared

1. Audited all 100 real Week1 rows and produced a normalized, grouped review
   manifest and source-hash audit. Sample: 20 original source IDs / 29 cases.
2. Implemented damage-type claim verification using the shared input/output
   classes, preserving Week2 predictions and abstaining for inadequate evidence.
3. Added an isolated advisory handoff for the three requested routes. It requires
   explicit upstream risk and verification facts and does not alter team modules.
4. Added JSON fixture, executable demo and pytest cases covering schema integration,
   boundary values, missing evidence, mismatches, source grouping and data audit.
5. Prepared the user-requested final root README cleanup to match the supplied
   screenshot. After this one edit, README files are frozen and must not be changed.
6. Added supported garment-region normalization and joint type/location checking.
   Exact regions match directly; a general `sleeve` or `knee` claim may match a
   detected left/right subregion. A side-specific claim with only a general detected
   region abstains, while two different supported regions produce a negative verdict.
7. Added a reproducible 12-case contract regression and multiclass metric generator.
   It reports 100% accuracy, macro precision, macro recall and macro F1 on the
   specified rule cases. These figures validate deterministic interface behaviour;
   the evaluation performs no image inference and is not a real-world model result.

## Validation scope

Run `python -m pytest tests/test_member2_week3.py -q`. The expanded suite contains
58 passing tests. Generate the scoped metric report with
`python -m src.damage_detection.evaluate_verification data/member2/week3/verification_cases.json data/member2/week3/verification_metrics.json`.
The local verification uses
the actual unchanged shared schema downloaded from the working branch. It checks
this new module and the real 100-case manifest; it is not a full repository
regression run or a new visual-model evaluation. Model weights/images were not
downloaded, training was not triggered, and no visual performance claim is made.

## Remaining research work

Independent clean controls, materialized ambiguous variants, second-person label
review, broader claim-language support and a real location-annotated image set
remain necessary. The current 100-case dataset has generic defect claims only, so
real location accuracy cannot be measured from it. The prepared audit makes these
gaps explicit rather than
creating ground truth from predictions or claims. Connecting this adapter inside
another member's workflow is outside the user's permitted edit scope.

## Submission boundary

Only the additive Member2 files and the explicitly requested final root README edit are proposed for
`member2-week6`. No commit, push, merge, PR or workflow dispatch has been performed.
The user must explicitly authorize any submission. The private repository is
readable in Chrome but not through the GitHub connector; whole-branch ZIP download
was blocked, so only necessary original files were downloaded for local testing.
