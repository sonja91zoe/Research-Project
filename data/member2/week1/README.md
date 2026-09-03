# Member 2 Week 1 image subset

This folder contains the 70 source images used by Hangyi Zhang's Week 1 and
Week 2 prototype: 35 images sampled from the holes dataset and 35 sampled from
the spots dataset. Images were resized/compressed and renamed for this project.

## Upstream datasets

- **Garment_condition_holes** — Wargön Innovation  
  https://huggingface.co/datasets/wargoninnovation/Garment_condition_holes
- **Garment_condition_spots** — Wargön Innovation  
  https://huggingface.co/datasets/wargoninnovation/Garment_condition_spots

Both upstream dataset pages identify the license as **Creative Commons
Attribution 4.0 International (CC BY 4.0)**. The dataset cards request the
reference: **CISUTAC project - Wargön Innovation**.

License: https://creativecommons.org/licenses/by/4.0/

Changes made for this project: a reproducible subset was selected, images were
compressed to JPEG with a maximum side of 1024 pixels and quality 80, and files
were renamed `hole_001.jpg`–`hole_035.jpg` and
`spot_001.jpg`–`spot_035.jpg`.

The derived CSV contains provisional project annotations and must not be
presented as annotations supplied by Wargön Innovation.

For image-only Week 2 evaluation, use
`data/member2/week2/image_manifest.csv` and the recovered upstream YOLO labels.
Do not derive image classes from Week 1 claim verdicts: a negative claim case
does not necessarily mean that its image is undamaged.
