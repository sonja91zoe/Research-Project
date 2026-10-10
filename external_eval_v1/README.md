# Frozen external evaluation set v1

Use this directory only for evaluation of Member 2 and the refund pipeline.
Do not include its images in training, validation for model selection, or
threshold tuning. `annotations/images.csv` records the human-assigned labels
and uncertainty; `orders/` contains separate synthetic evaluation orders.
Neither an order field nor a model prediction is ground truth for image damage.

The images have mixed provenance. The jacket and T-shirt `SELF-*` images are
self-taken; several other `SELF-*` and `DAM-*` images are AI-generated
synthetic evaluation examples, as noted in the annotation sheet. Do not
describe the entire set as real-world customer photos.

The annotation sheet contains 18 image rows. `DAM-HOD-02.jpg` is a
crop/framing ablation of `DAM-HOD-01.jpg`, **not an independent sample**. Keep
the pair in the same group when reporting counts or splitting analyses.
`DAM-HOD-03.jpg` is the annotated stain example. `DAM-HOD-03.png` is a
near-identical export of that JPG. It and `SELF-SRT-02.jpg` have no annotation
rows and are not part of this frozen evaluation list.

The `UNKNOWN` annotations remain unknown. Do not turn them into positive or
negative damage labels from filenames, order text, or model output.
