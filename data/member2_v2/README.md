# Member 2 v2 pilot training data

This is a small **synthetic training pilot**, not a real-world damage dataset. The
15 distinct source images are primarily AI-generated: five `hole_or_tear`, five
`stain_or_spot`, and five `clean`. Their contents and annotations should not be
presented as independent evidence of performance on customer photos.

`raw/` holds the 15 sources and `raw_labels/` holds their YOLO annotations.
`images/` and `labels/` contain copies arranged by class into train (3),
validation (1), and test (1) per class. The clean labels are intentionally
empty because there is no damage box. The split files are copies of the raw
files, not 15 additional samples. `dataset.yaml` resolves its image paths from
its own directory so it works outside the original developer's machine.

The annotation helper is `scripts/annotate_member2_v2.py`. Local YOLO run
outputs, cache files, and pilot weights are excluded from this commit. The
existing deployed `models/member2/best.pt` is unchanged; this pilot does not
replace or validate that production model.

`external_eval_v1/` is a **frozen evaluation set**. Do not copy its images or
labels into this training dataset, use them to adjust thresholds, or retrain
on them. Report results on the pilot data separately from results on external
evaluation images.
