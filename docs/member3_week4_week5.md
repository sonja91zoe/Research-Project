# Member 3 - Week 4 and Week 5

## Scope

This prototype supplies the order, policy, and evidence-verification layer. All
policy and order records are synthetic and must not be interpreted as a real
merchant's refund terms or customer data.

## Week 4 deliverables

- Mock policy knowledge base with traceable policy IDs and sources.
- Mock order database containing 12 orders.
- Twelve complete refund test cases covering eligible and difficult cases.
- Structured `OrderRecord`, `RetrievedPolicy`, and `VerifiedEvidence` schemas.

## Week 5 deliverables

- Case-insensitive order lookup by order ID.
- Deterministic top-k policy retrieval using keyword overlap.
- Evidence verification for order validity, image-order match, policy
  eligibility, policy match, completeness, refund amount, and policy source.
- Automated tests for retrieval, traceability, difficult cases, and all 12
  expected eligibility outcomes.

## Limitations

This is a reproducible V1 baseline, not a semantic embedding model. The policy
KB can later be replaced with approved merchant policies, and the lexical
retriever can later be compared with an embedding-based RAG implementation.
