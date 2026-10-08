# Photo-matched synthetic catalog

`photo_matched_orders.json` pairs ORD001–ORD070 with the existing Member 2
H001–H035 and S001–S035 photos. Categories were assigned by assistant visual
inspection, not copied from detector predictions; human confirmation is pending.
Unknown categories remain unknown. This is not proof of actual product identity
or a real purchase. Original simulated transaction fields are retained.

The original `orders.json`, historical records and default webpage catalog are
unchanged. Do not import these same-ID revised orders into an existing case
database; use an isolated evaluation catalog/database. Review the pairings in
`photo_matched_review.html` from a local checkout.

From the repository root:

```sh
PYTHONPATH=. python scripts/build_photo_matched_orders.py
PYTHONPATH=. python scripts/test_member2_70_flow.py --photo-matched --delivered-scenario
```

The second command performs real model inference, requiring repository YOLO
weights and the CLIP dependencies/cache. It uses a separate snapshot with
simulated delivered/non-final-sale orders and seeded request dates within 30
days of purchase. Prices and thresholds are not lowered to obtain approvals.
No payments occur. Dataset-derived claims and possible training overlap mean
this is an integration test, not an independent accuracy estimate.

Local run 2026-10-09: 70 completed, 0 execution errors; 28 human review,
42 request-more-evidence, 0 auto-refund. Compared with the earlier identical
delivery scenario, product-mismatch decision reasons fell from 49 to 8.
These are routing counts, not validated prediction accuracy.
