# Prototype integration handoff

The deployed damage weight remains `models/member2/best.pt`. This update does not train or replace weights. Prototype damage-review gates are now shared across detection and claim verification: review threshold 0.15; detected damage below 0.10 requests clearer evidence in the decision engine. These are provisional workflow settings, not calibrated probabilities or an accuracy claim. The usual order/policy and image-quality overrides still apply.

Local SQLite mode, date verification and correction history are described in `local_sqlite_workflow.md`. Do not enable the single-user SQLite mode on a public deployment without authentication and access controls. No public deployment change is part of this merge.

The photo review and comparison scripts are optional research utilities, not runtime dependencies. External images, human-review JSON, generated HTML, result reports containing case information, model caches, candidate training artifacts and the local case database are intentionally not shipped. Existing repository model and dataset assets are unchanged.

- `build_member3_dataset_manifest`: creates a pending-review manifest from existing repository orders/photos, refuses to overwrite one.
- `build_photo_review`: builds the primary-dataset review page from that manifest and the existing annotation CSV.
- `test_external_pending`: runs local YOLO on PNG files in `data/external_test_pending`.
- `build_external_review`: requires the locally generated `artifacts/external_image_test_20261008_170246/results.json` and matching original photos; generates an offline review form.
- `compare_external_weights`: requires the external photos, `external_photo_human_review.json`, and all three local weight paths listed in the script. Uses common 512 inference settings; discoloration is excluded from the two-class agreement denominator.
- `validate_external_workflow`: requires the same external photos and review JSON; uses synthetic orders and actual inference. `--upload-copies` optionally uses separately prepared JPEG files in `upload_copies`. Approvals are simulated; photo re-submission is not new evidence.

Missing private/local inputs are expected on a fresh clone: supply your own authorized dataset before running these optional utilities. Human labels never replace model predictions. Do not claim an independent final-test score after using the same samples for model selection.
