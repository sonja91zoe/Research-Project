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
python -m scripts.member2_realtime_demo --image path/to/garment.jpg --claim-text "The jacket has a visible tear." --weights models/member2/best.pt
```

The command calls the real YOLO backend, then returns the existing structured claim-image verification result. Low-confidence detections and missing visual evidence remain routed to human review.

## Agent configuration

The local and Streamlit workflows automatically use the bundled weight. Direct Agent callers can pass a weight path or set `MEMBER2_YOLO_WEIGHTS`; the CLIP fallback remains available when no weight exists.
