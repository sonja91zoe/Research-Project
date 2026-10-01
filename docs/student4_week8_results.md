# Student 4 Week 8: Pilot Results

## Scope

This is a controlled structured-evidence pilot with 10 validation cases and 6 test cases. Labels were manually specified using the project's initial decision rubric, which favors conformity to rule-based behavior. It is not a real-image accuracy study or an independent expert-labelled benchmark.

## Validation and Threshold Selection

At the original 0.80 threshold, rule-based decisions matched 10/10 validation labels and ML decisions matched 8/10. ML returned automatic refunds for W8_V07 (score 0.83) and W8_V08 (score 0.97), contrary to the synthetic rubric.

Increasing the ML threshold to 0.90 changed W8_V07 to a request for evidence. W8_V08 remained an incorrect automatic refund. Both 0.90 and 0.95 matched 9/10 validation labels with one incorrect automatic refund. The lower tied threshold, 0.90, was selected. This tie-break was chosen after examining validation results but before test evaluation.

Rule threshold 0.80 was retained. Higher rule thresholds increased evidence requests and reduced agreement with the initial rubric. Application defaults were not modified by these experiments.

## Test Results

| Method | High threshold | Label agreement | Incorrect auto-refunds |
|---|---:|---:|---:|
| rule | 0.80 | 6/6 | 0 |
| ml | 0.90 | 6/6 | 0 |
| Direct LLM (ChatGPT web, shared conversation; model unrecorded) | Not applicable | 6/6 | 0 |

The same six structured cases were used for each method. LLM prompts contained general decision guidance but no per-case labels, rule/ML predictions or weighted scoring formula. Prompt design therefore forms part of the baseline; this is not an unguided LLM assessment.

## Manual LLM Provenance

Six responses were supplied by the user and preserved. The user confirmed ChatGPT web with thinking intensity High for all six cases, sent sequentially in the same conversation. The screenshot shows High thinking intensity, not a model identifier. Model/version, run timestamps and retry history remain unrecorded; first-response selection is not independently verified.

This deviated from the planned separate-conversation protocol in the original prompt manifest. The manifest is retained as the planned protocol. Earlier prompts and responses may affect later cases; this run is an exploratory sequential-session pilot, not six independent per-case runs. The source paste contains escaped underscores; the source text is retained and parsing removes only these escapes. No decisions or explanations were corrected.

The six label matches are retained, but do not constitute a controlled independent-case LLM baseline.

## Second LLM Collection

A second set of responses was supplied following the request for one new conversation per case. All six decisions match the test labels and all six match Round 1. The second collection is stored separately in `data/member4/week8/llm_responses_round2` and `data/results/student4_week8/llm_comparison_round2.json`.

The user confirmed one fresh conversation per case, High thinking intensity, unchanged prompts and first-completed-response selection for this round; browser execution was not independently observed. Model/version, timestamps and retry history remain unrecorded. The original pasted text is preserved; parsing removes only underscore escapes and backslashes immediately before line breaks.

These are repeated responses to the same six cases, not twelve unique test cases. Matching decisions across these two collections does not establish statistical equivalence, general stability, or real-world reliability.

## Interpretation and Limitations

All three methods matched the six test labels. This does not establish real-world reliability, statistical equivalence or model superiority. Each test class contains only two cases. The pilot has related synthetic scenarios across validation and test splits and is not a claim of broad independent generalization. Two manual collections are available, but no systematic repeated-run LLM stability study was performed. ML used the Week 6 synthetic-data model and two-decimal confidence outputs.

## Remaining Work

- Record model/version if available; do not infer it from the thinking-intensity setting.
- The second collection follows the fresh-conversation protocol according to user confirmation.
- Expand evaluation with separately reviewed labels and realistic varied evidence.
- Automated checks now cover experiment provenance, boundaries and overwrite protection.
- The local webpage now accepts actual image uploads and calls the Week 7 Agent pipeline.
- Evidence resubmission, saved review actions and simulated refund confirmation have automated coverage; manual browser acceptance is still pending.
- Commit and upload the Week 8 changes after verification.
