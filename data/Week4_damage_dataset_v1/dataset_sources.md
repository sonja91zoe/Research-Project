# Dataset Sources and Provenance

## Source pools

| Local source name | Local pool used | Available at sampling | Selected | Source labels |
|---|---|---:|---:|---|
| `Garment_condition_holes` | `holes/train/images` + `holes/valid/images` | 761 | 35 | Corresponding YOLO `.txt` labels were copied for the original candidate export |
| `Garment_condition_spots` | `spots/train/images` | 500 | 35 | No labels were supplied in the downloaded source; Week 1 uses visual triage |

The source folders were stored locally under `E:\Research Project\holes` and `E:\Research Project\spots`. Candidates were sampled reproducibly with Python `random.seed(32933)`, compressed to JPEG with a maximum side of 1024 pixels and quality 80, and renamed `hole_001.jpg`–`hole_035.jpg` and `spot_001.jpg`–`spot_035.jpg`.

## Provenance rules

- `source_image_id` is the stable link to one of the 70 selected photographs.
- `file_name`, `source_dataset`, `source_pool`, and `source_folder` preserve the trace back to the sampled pool.
- `case_origin=source_image_claim` means the claim is intended to match the visual condition.
- `case_origin=altered_claim_same_source_image` means the image is reused with a deliberately false or mismatched claim.
- `case_origin=constructed_ambiguous_variant` means the row is a recipe for a crop/blur/occlusion/contrast/incomplete-view derivative. The derivative is not yet a separate independent source photograph.

## Known limitations

The original upstream URLs, licenses, and pre-rename file paths were not retained in the uploaded conversation. Before public distribution or model training, recover those records from the dataset README files or download metadata and add them to a formal manifest. This Week 1 package is appropriate for schema, module integration, and controlled prototype evaluation; it is not yet a publication-ready benchmark.
