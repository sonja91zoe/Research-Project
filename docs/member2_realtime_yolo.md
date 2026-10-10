# Member 2 realtime YOLO handoff

The Member 2 adapter can run a persisted YOLO detector for a newly supplied image. The deployable weight is bundled at `models/member2/best.pt`; callers may override it with `MEMBER2_YOLO_WEIGHTS`.

## Obtain the weight

To reproduce or replace the bundled weight, run the **Week 2 YOLO training** GitHub Actions workflow. Its trained file is located at:

```text
artifacts/member2_yolo/damage_detector/weights/best.pt
```

Keep a long-term copy in the team shared drive. Replace `models/member2/best.pt` deliberately or set `MEMBER2_YOLO_WEIGHTS` to an absolute path for a local comparison.

## Run one real image

Install the YOLO dependencies and run:

```text
python -m pip install -r requirements-yolo.txt
python -m scripts.member2_realtime_demo --image path/to/garment.jpg --claim-text "The jacket has a visible tear."
```

By default the command uses `models/member2/best.pt` for YOLO damage detection and CLIP for independent product classification. `--weights` or `MEMBER2_YOLO_WEIGHTS` selects a different YOLO weight. `--backend clip` explicitly runs the historical CLIP damage baseline. Low-confidence detections and missing visual evidence remain routed through the existing review rules.

## Agent configuration

Refund Studio, the local HTTP workflow, `run_pipeline()`, and direct Member 2 Agent calls use the same YOLO damage and CLIP product defaults. Missing or invalid YOLO weights and missing YOLO dependencies raise clear errors; they do not silently select CLIP damage detection. Injected detectors remain available for controlled tests and explicit research runs.

Agent and pipeline results include `member2.runtime_metadata`: separate damage and product model identities, the YOLO weights SHA-256, and flags showing whether each inference ran. Quality-gated images retain the configured identities but mark both inference flags false.
