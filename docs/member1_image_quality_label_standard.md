# Member 1 — Image Quality Label Standard V1

## 1. Purpose

This document defines the first version of the image-quality labelling standard used in the refund evidence assessment module.

The goal is to determine whether a customer-uploaded image is sufficiently clear, complete, and usable for further refund assessment.

The main quality dimensions are:

- Blur
- Lighting
- Cropping / Completeness
- Occlusion
- Relevant Region Visibility
- Overall Image Usability


---

## 2. Blur Labels

### Clear

Definition:

The main product details and the claimed damage region are clearly visible.

Characteristics:

- Product edges are clear
- Fine details can be identified
- Damage can be visually inspected
- No significant motion blur

Expected usability:

Usable


### Slightly Blurred

Definition:

The image contains some blur, but the product and possible damage can still be reasonably inspected.

Characteristics:

- Some details are reduced
- Product remains identifiable
- Damage region is still visible
- Evidence may still be usable

Expected usability:

Usually usable


### Severely Blurred

Definition:

The image is too blurred to reliably identify the product condition or claimed damage.

Characteristics:

- Product details are difficult to distinguish
- Damage cannot be reliably confirmed
- Important visual evidence is lost

Expected usability:

Not usable


---

## 3. Lighting Labels

### Normal Lighting

Definition:

The product and relevant damage region are clearly visible under appropriate lighting.

Characteristics:

- Details are visible
- Colours are reasonably distinguishable
- No important region is hidden by darkness or excessive brightness

Expected usability:

Usable


### Dark

Definition:

The image is underexposed and important product details are difficult to identify.

Characteristics:

- Important regions appear too dark
- Damage details may be hidden
- Product condition cannot be reliably inspected

Expected usability:

May be unusable depending on severity


### Overexposed

Definition:

The image is excessively bright and important visual details are lost.

Characteristics:

- Bright regions lose texture
- Damage details may disappear
- Product condition is difficult to inspect

Expected usability:

May be unusable depending on severity


---

## 4. Cropping / Completeness Labels

### Complete

Definition:

The relevant product area and the claimed damage region are sufficiently visible.

Characteristics:

- Required evidence region is included
- Product context is visible
- Damage location can be assessed

Expected usability:

Usable


### Partial

Definition:

Part of the product is outside the image, but the claimed damage region is still visible.

Characteristics:

- Product context is incomplete
- Relevant damage region remains visible
- Assessment may still be possible

Expected usability:

Usually usable


### Insufficient

Definition:

Important evidence is missing because the image is cropped too heavily.

Characteristics:

- Claimed damage region is not shown
- Product cannot be sufficiently verified
- Important visual context is missing

Expected usability:

Not usable


---

## 5. Occlusion Labels

### No Occlusion

Definition:

The relevant product and damage region are fully visible.

Examples:

- No hand covering the damage
- No object blocking the garment
- No folded fabric hiding the relevant region

Expected usability:

Usable


### Partial Occlusion

Definition:

A small part of the relevant product region is blocked, but the evidence can still be assessed.

Expected usability:

May still be usable


### Heavy Occlusion

Definition:

The claimed damage region or important product details are significantly blocked.

Examples:

- Hand covers the tear
- Clothing is folded over the damaged area
- Another object blocks the evidence

Expected usability:

Not usable


---

## 6. Relevant Region Visibility

### True

The region mentioned in the customer claim is visible in the uploaded image.

Example:

Customer claim:

"The jacket has a tear on the left sleeve."

The uploaded image clearly shows the left sleeve.

Label:

`relevant_region_visible = true`


### False

The region mentioned in the customer claim is not sufficiently visible.

Example:

Customer claim:

"The jacket has a tear on the left sleeve."

The uploaded image only shows the front body of the jacket.

Label:

`relevant_region_visible = false`


---

## 7. Overall Image Usability

### Usable

An image is considered usable when:

- The product can be identified
- Image quality is sufficient
- The relevant region is visible
- The image is not severely blurred
- Lighting does not prevent inspection
- Occlusion does not block critical evidence


### Not Usable

An image is considered not usable when one or more critical conditions prevent reliable evidence assessment.

Examples:

- Severe blur
- Relevant damage region not visible
- Heavy occlusion
- Extreme darkness
- Extreme overexposure
- Important product area missing


---

## 8. Suggested V1 Label Structure

Each image should be manually labelled using the following fields:

```json
{
  "case_id": "REFUND_001",
  "blur_label": "clear",
  "lighting_label": "normal",
  "cropping_label": "complete",
  "occlusion_label": "none",
  "relevant_region_visible": true,
  "image_usable": true
}