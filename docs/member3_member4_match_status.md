# Member 3–4 image/order match status integration

Date: 8 October 2026

## Problem

The previous evidence verifier represented a missing upstream
`detected_product` value as an image/order score of `0.0`. It then treated the
missing value as a confirmed mismatch and made the case policy-ineligible. The
local web endpoint also copied the selected order category into
`detected_product`, which made the comparison self-confirming rather than an
independent visual check.

## Change

Member 3 now reports one of three explicit states:

- `MATCH`: an available visual product label matches the order product or
  category;
- `MISMATCH`: an available visual product label conflicts with the order;
- `NOT_AVAILABLE`: no independent visual product label was supplied.

`NOT_AVAILABLE` uses a neutral numeric consistency value of `0.5` for backward
compatibility with Member 4 confidence features. It does not by itself make an
otherwise eligible order policy-ineligible. `MISMATCH` remains a hard Member 4
human-review override. Older saved Member 3 records infer their status from the
legacy numeric value.

The local endpoint no longer fills `detected_product` from the selected order.
The system therefore does not claim an independent image/order match when no
product classifier exists.

## Verification

- Member 3/4 focused regression suite: 70 passed.
- Full repository suite: 149 passed, with 40 existing joblib/NumPy deprecation
  warnings.
- Six manual Member 3 flow cases passed.

### Controlled 70-order regression comparison

This comparison used the 70 synthetic order records and fixed high-quality
evidence values, with `detected_product` deliberately unavailable. It tests the
rule change only; it is not real-image model performance.

| Result | Previous rules | Tri-state rules |
|---|---:|---:|
| Human review | 70 | 59 |
| Automatic refund | 0 | 11 |
| Policy eligible | 0 | 54 |
| Human-review rate | 100.0% | 84.3% |

The remaining reviews are primarily the existing medium/high refund-risk
matrix, plus ten non-delivered and six final-sale synthetic orders.

### Real 70-image YOLO check

A newly trained local YOLO11n candidate completed 20 CPU epochs in 1,934.96
seconds. On the held-out 70-image set it reached 54.3% end-to-end accuracy and
64.6% macro F1. The teammate `member2-realtime-YOLO` candidate performed better:
65.7% end-to-end accuracy and 68.2% macro F1.

Both candidates produced detection confidences below the existing `0.70`
human-review threshold on all 70 held-out images. Consequently, the current
end-to-end Agent still sends these real-image cases to review or requests more
evidence. The threshold must be calibrated by Member 2 on a separate validation
set; it must not be lowered on the held-out set merely to improve automation.

## Remaining boundary

The damage detector predicts holes/tears and stains/spots. It does not yet
identify garment categories. Member 2 (or another visual product classifier)
must supply `detected_product` and its confidence. Member 3 owns the comparison
with the retrieved order; Member 4 owns the risk decision.
