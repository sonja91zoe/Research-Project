# Member 2 realtime YOLO handoff

The Member 2 adapter can run a persisted YOLO detector for a newly supplied image. The binary weight is deliberately excluded from ordinary Git history.

## Obtain the weight

Run the **Week 2 YOLO training** GitHub Actions workflow from the `member2-realtime-YOLO` branch. Download the `member2-week2-yolo-model` artifact before its 90-day expiry. The trained file is located at:

```text
artifacts/member2_yolo/damage_detector/weights/best.pt
```

Keep a long-term copy in the team shared drive. For local use, place it at `models/member2/best.pt` or set `MEMBER2_YOLO_WEIGHTS` to its absolute path.

## Run one real image

Install the YOLO dependencies and run:

```text
python -m pip install -r requirements-yolo.txt
python -m scripts.member2_realtime_demo --image path/to/garment.jpg --claim-text "The jacket has a visible tear." --weights models/member2/best.pt
```

The command calls the real YOLO backend, then returns the existing structured claim-image verification result. Low-confidence detections and missing visual evidence remain routed to human review.

## Agent configuration

Set `MEMBER2_YOLO_WEIGHTS=models/member2/best.pt` before starting any Agent process that calls `run_member2` or `run_member2_verification`. When neither a weight argument nor this environment variable is supplied, the existing CLIP fallback remains unchanged for backwards compatibility.
