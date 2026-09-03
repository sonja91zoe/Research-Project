# Research Project

Project skeleton for a risk-aware refund AI system.

## Structure

- `data/`: images, claims, policies, and orders
- `src/image_quality/`: image quality assessment
- `src/damage_detection/`: damage detection
- `src/evidence/`: retrieval, order evidence, and verification
- `src/decision/`: confidence, risk, and decision logic
- `src/agent/`: workflow agent
- `notebooks/`: research notebooks
- `tests/`: automated tests
- `app/`: application entry points

## Member 2 — Damage Detection V1

Hangyi Zhang's Week 2 image-only damage detector is in `src/damage_detection/`.
It uses the shared `Member2Output` schema, preserves the Week 1 damage labels,
and routes poor evidence or low-confidence predictions to human review. See
`docs/member2_week2.md`. GitHub Actions runs its tests and the free CLIP
full-image-plus-YOLO-crop evaluation on `student2-week5`.

