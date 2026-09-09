# Member 1 — Week 3 Evaluation and Stabilisation

## 1. Objective

The objective of Week 3 is to stabilise and evaluate the Image Quality Module V1 under different image-quality conditions and record failure cases.

The evaluation focuses on three outputs:

- Blur classification
- Lighting classification
- Overall image usability

The current controlled evaluation dataset contains 10 manually labelled images prepared in Week 1.


## 2. Initial Evaluation

The original Week 2 module was evaluated against the manual labels in:

`data/member1/image_quality_labels_v1.csv`

Initial results:

- Blur accuracy: 8/10 (80.0%)
- Lighting accuracy: 10/10 (100.0%)
- Usability accuracy: 10/10 (100.0%)


## 3. Initial Failure Cases

Two blur-classification mismatches were identified.

### Failure Case 1 — Dark Hoodie

Case:

`IMAGE_007`

Image:

`data/member1/images/member1_hoodie_001_dark.jpg`

Manual blur label:

`clear`

Initial prediction:

`slightly_blurred`

Observed blur scores:

- Normal hoodie: approximately 366.14
- Dark hoodie: approximately 53.80

Analysis:

The image itself was not intentionally blurred, but the low-light condition reduced visible edges and local contrast. Because the original blur detector used Laplacian variance directly on the grayscale image, the dark image produced a much lower blur score.

This indicates that lighting conditions can interfere with blur estimation.


### Failure Case 2 — Occluded Jacket

Case:

`IMAGE_010`

Image:

`data/member1/images/member1_jacket_001_occluded.jpg`

Manual blur label:

`clear`

Initial prediction:

`slightly_blurred`

Observed blur scores:

- Normal jacket: approximately 200.40
- Occluded jacket: approximately 181.21

Analysis:

The occluded image remained visually clear, but the added occlusion reduced the amount and distribution of high-frequency edge information.

The image score also fell close to the original `clear` threshold of 200, creating a borderline classification error.


## 4. Stabilisation Method

To reduce the influence of lighting conditions on blur estimation, histogram equalisation was added before Laplacian variance calculation.

Updated blur-processing pipeline:

1. Load image
2. Convert image to grayscale
3. Apply histogram equalisation
4. Calculate Laplacian variance
5. Classify blur level

The updated implementation uses:

`cv2.equalizeHist()`

before calculating Laplacian variance.


## 5. Stabilised Blur Scores

After histogram equalisation, the 10-image controlled dataset produced the following blur scores:

| Case | Manual Blur Label | Stabilised Blur Score |
|---|---|---:|
| IMAGE_001 | clear | 2245.85 |
| IMAGE_002 | clear | 477.51 |
| IMAGE_003 | clear | 525.29 |
| IMAGE_004 | clear | 1138.51 |
| IMAGE_005 | slightly_blurred | 44.85 |
| IMAGE_006 | severely_blurred | 20.85 |
| IMAGE_007 | clear | 640.55 |
| IMAGE_008 | clear | 1542.96 |
| IMAGE_009 | clear | 4304.74 |
| IMAGE_010 | clear | 964.03 |

The controlled dataset showed a large separation between the manually labelled clear and blurred images.


## 6. Stabilised Thresholds

The Week 3 stabilised V1 thresholds are:

- `blur_score < 30` → `severely_blurred`
- `30 <= blur_score < 150` → `slightly_blurred`
- `blur_score >= 150` → `clear`

These thresholds are provisional and were selected based on the current controlled evaluation dataset.

They should not be interpreted as universal blur thresholds.


## 7. Final Evaluation Results

After stabilisation:

- Blur accuracy: 10/10 (100.0%)
- Lighting accuracy: 10/10 (100.0%)
- Usability accuracy: 10/10 (100.0%)

No mismatches were found on the current 10-image controlled evaluation dataset after stabilisation.


## 8. Before and After Comparison

| Metric | Before Stabilisation | After Stabilisation |
|---|---:|---:|
| Blur Accuracy | 80.0% | 100.0% |
| Lighting Accuracy | 100.0% | 100.0% |
| Usability Accuracy | 100.0% | 100.0% |

The main improvement occurred in blur classification.

Histogram equalisation reduced the sensitivity of Laplacian-based blur assessment to dark and partially occluded image conditions in the current dataset.


## 9. Current Limitations

The current evaluation has several limitations:

- The evaluation dataset contains only 10 images.
- The same controlled dataset was used to identify failure cases and refine thresholds.
- The current 100% result therefore represents agreement on the controlled evaluation dataset, not real-world generalisation performance.
- More images from different devices, backgrounds, fabrics, colours, lighting conditions, and customer-upload scenarios are required for broader validation.
- Occlusion is not currently detected automatically. Relevant-region visibility is still provided as an input signal.
- The current thresholds remain heuristic and may require further recalibration when the dataset grows.


## 10. Week 3 Outcome

Week 3 successfully:

- Evaluated the Image Quality Module under different controlled image-quality conditions
- Identified two initial blur-classification failure cases
- Analysed the causes of those failures
- Stabilised blur assessment using histogram equalisation
- Recalibrated provisional blur thresholds
- Improved blur-label agreement from 80% to 100% on the current controlled dataset
- Recorded evaluation results, failure cases, stabilisation method, and limitations

The Image Quality Module is now more stable for the current controlled prototype dataset.