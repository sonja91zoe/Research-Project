# Member 3 dataset roles

The original Member 2 photos remain the primary integration inputs, linked by
the existing synthetic order IDs. Do not replace historical orders or reports.
Run `python -m scripts.build_member3_dataset_manifest` once to create a review
manifest with source IDs, paths and SHA-256 hashes. A second run refuses to
overwrite potential human review edits.

All garment categories start unverified. The manifest records historical mock
categories separately from verified labels. A reviewer must inspect each image;
leave the verified category null when a close-up cannot establish garment type.
An order association in this manifest is not proof of a genuine purchase.
The manifest is an audit artifact, not yet a UI routing override.

Human review is an appropriate outcome for unresolved identity. Member 3 should
report missing evidence; Member 4 owns the final route. A review queue must not
mark the product MATCH, approve a refund, or count the case as a model error
solely because the photograph lacks a full-garment view. Existing decision
rules do not guarantee every NOT_AVAILABLE case goes directly to HUMAN_REVIEW.

Zenodo is a separate external evaluation source. The current 70-image evaluation
has already been run. Repeated inference alone does not invalidate a fixed test
set, but using results to choose models, prompts, rules or thresholds makes that
set development/validation data for subsequent versions. Do not call it unseen
or independent final evidence without a documented usage audit.

For a fresh final test set, lock sample IDs, labels, model version and thresholds
before evaluation. Exclude exact and near duplicates and group views of the same
garment together across splits. Training overlap with pretrained models may be
unknown and must be disclosed. Order dates and amounts remain synthetic in
end-to-end scenarios. Report module errors separately from final routing.
