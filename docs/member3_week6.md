# Member 3 - Week 6 Single-Case Evidence Chain

## Objective

Connect the structured outputs from Members 1 and 2 to Member 3 order and
policy retrieval, then return the existing `Member3Output` interface together
with a traceable evidence chain.

## Pipeline

1. Validate that the case and upstream outputs share the same case ID.
2. Read the customer claim and image paths from `CaseInput`.
3. Read image usability from `Member1Output`.
4. Read damage and claim-image consistency from `Member2Output`.
5. Retrieve the order by order ID.
6. Retrieve the most relevant mock refund policy.
7. Verify order validity, image-order consistency, policy eligibility, and
   evidence completeness.
8. Return both a traceable `EvidenceChain` and a downstream-compatible
   `Member3Output`.

## Safeguards

- Reject mismatched case IDs.
- Mark unusable images as policy-ineligible.
- Mark claim-image consistency below 0.50 as policy-ineligible.
- Preserve order and policy sources for traceability.

## Limitations

The upstream outputs and refund policy remain mock inputs. This Week 6 version
proves the integration contract; real Member 1/2 modules and approved merchant
policies can replace the mocks without changing the Member 3 output schema.
