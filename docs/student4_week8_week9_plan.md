# Student 4 Week 8–9: Experiments and Interactive Refund Prototype

## Added Requirement

Deliver a browser-based refund workflow that guides a user from
starting a refund request to a recorded prototype outcome.

Extend the existing app instead of creating a separate native app.

## User Workflow

1. Start a refund request.
2. Select or enter an order.
3. Enter the refund reason and upload one image.
4. Submit the request and display processing status.
5. Run the actual image-quality, damage-detection, evidence-verification
   and decision pipeline.
6. Display the decision, reasons and relevant order/policy evidence.
7. Support the appropriate next action:
   - AUTO_REFUND: confirm and record a simulated refund.
   - REQUEST_MORE_EVIDENCE: provide guidance, upload replacement
     evidence and run the assessment again.
   - HUMAN_REVIEW: record a pending review and provide a prototype
     reviewer screen with evidence, comments and a recorded outcome.

Preserve the original automated recommendation when recording a
human review outcome.

## Acceptance Criteria

- Uploaded image content reaches the Python analysis pipeline.
- Visual results are derived from the uploaded image rather than
  hard-coded scores or damage labels.
- The interface supports the backend's current single-image limit.
- Required inputs, invalid images and processing errors are handled
  with clear messages.
- A failed backend request must not display a fabricated success result.
- Results and subsequent actions remain associated with the same case.
- Supplementary evidence creates an identifiable reassessment.
- Demonstration fixtures are clearly distinguished from real inference.
- Refund confirmation changes prototype state only; no money is moved.
- Current missing visual evidence remains visible and is not invented.

## Week 8 Research

Compare direct LLM decisions, rule-based confidence and ML-assisted
confidence using a documented common evaluation set.

Keep evaluation cases separate from model-training data.
Distinguish synthetic controlled evaluation from real-image evaluation.

Run confidence-threshold experiments and inspect incorrect refunds,
unnecessary reviews and evidence requests.

Choose thresholds using validation cases, then report performance on
held-out test cases. Record the code version and experiment settings.

Without an LLM API, collect real model responses manually through
an available model interface. Use a fixed prompt and fresh conversations,
and record the model name, date, inputs and original responses.

Do not fabricate missing LLM results or present pending comparisons
as completed experiments.

## Schedule

### Week 8
- Define evaluation cases and labels.
- Run rule-based and ML comparisons and threshold experiments.
- Collect direct LLM baseline responses.
- Connect the existing webpage to real image upload and Agent inference.
- Implement results and evidence-resubmission flow.

### Week 9
- Complete and verify the prototype human-review flow.
- Fix usability and integration problems.
- Analyse errors and document module limitations.
- Finalise the report, demonstration cases and presentation or recording.

## Scope and Limitations

The prototype runs locally in a browser with local order and policy data.
External LLM API access is not required for the refund interface.

The current damage module does not supply all product, location and
claim-consistency evidence. These gaps can route real cases to review.

ML confidence uses the Week 6 synthetic-data model and requires further
evaluation. Controlled demonstrations are not evidence of real-world
refund accuracy.