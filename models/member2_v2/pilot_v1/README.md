# Member2 YOLO v2 pilot_v1

- Model: Member2 YOLO v2 pilot_v1
- Base model: `yolo11n.pt`
- Weights file: `best.pt`
- SHA-256: `EF09BFCFB7D1B280BA23BFA36B4389FCAD1349AA378C1B72CA6EA8A67EDD3885`
- File size: 5,462,874 bytes

Training data: Member2 v2 pilot synthetic dataset (`data/member2_v2/`).
The 15 images are primarily AI-generated synthetic training examples, not
real-world customer photos.

Dataset size: 15 distinct images

Classes / dataset composition:
- 5 `hole_or_tear`
- 5 `stain_or_spot`
- 5 `clean` (empty damage-box labels; clean is not a YOLO output class)

Split:
- train: 9
- val: 3
- test: 3

Training configuration:
- Epochs: 50
- Image size: 640
- Batch size: 4
- Seed: 42

This is a pilot model, not the final model. `external_eval_v1` was not used
for training, validation, or threshold tuning. The existing
`models/member2/best.pt` remains unchanged and remains the default runtime
weight unless a different path is explicitly selected.
