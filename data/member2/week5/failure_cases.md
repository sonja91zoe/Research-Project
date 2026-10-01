# Week 5 failure-case review

Auto-generated from measured outputs. It records factual mismatches and review flags; visual root causes require human inspection and are not inferred here.

| Case ID | Source image ID | Category | Damage: expected → predicted | Claim: expected → predicted | Confidence | Verification reason |
| --- | --- | --- | --- | --- | --- | --- |
| DDV1-001 | H001 | original_image_matching_claim | hole_or_tear → uncertain | positive → ambiguous | 0.471375 | visual_review_required |
| DDV1-002 | H002 | original_image_matching_claim | hole_or_tear → stain_or_spot | positive → negative | 0.816086 | damage_type_mismatch |
| DDV1-003 | H003 | original_image_matching_claim | hole_or_tear → stain_or_spot | positive → negative | 0.839101 | damage_type_mismatch |
| DDV1-004 | H004 | original_image_matching_claim | hole_or_tear → no_damage | positive → ambiguous | 0.502832 | visual_review_required |
| DDV1-005 | H005 | original_image_matching_claim | hole_or_tear → stain_or_spot | positive → negative | 0.823061 | damage_type_mismatch |
| DDV1-006 | H006 | original_image_matching_claim | hole_or_tear → stain_or_spot | positive → ambiguous | 0.597256 | visual_review_required |
| DDV1-007 | H007 | original_image_matching_claim | hole_or_tear → uncertain | positive → ambiguous | 0.449843 | visual_review_required |
| DDV1-008 | H008 | original_image_matching_claim | hole_or_tear → stain_or_spot | positive → negative | 0.824960 | damage_type_mismatch |
| DDV1-009 | H009 | original_image_matching_claim | hole_or_tear → stain_or_spot | positive → negative | 0.847954 | damage_type_mismatch |
| DDV1-010 | H010 | original_image_matching_claim | hole_or_tear → no_damage | positive → ambiguous | 0.669462 | visual_review_required |

Showing the first 10 of 58 measured failure/review rows; use `week5_results.csv` for the complete list.
