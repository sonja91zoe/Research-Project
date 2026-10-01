# Local interactive refund workflow

Start from the repository root with the existing virtual environment:

```sh
source .venv/bin/activate
python -m app.server
```

Open http://127.0.0.1:8765 in a browser. Stop the server with Ctrl+C.

## User flow

1. Select a local demonstration order, enter the request date and an English claim, upload one JPEG/PNG, and explicitly state whether the claimed region is visible.
2. Actual image bytes are decoded and saved locally, then processed by the Week 7 image-quality, CLIP damage, order/policy and Agent pipeline. No browser-supplied confidence values or manufactured product matches are accepted.
3. A request for evidence allows another photo to be assessed. The old photo and assessment remain in the record.
4. A human-review recommendation opens a local demonstration reviewer form. A named reviewer and note are required for approval, rejection or an evidence request. The original Agent assessment is retained.
5. Approved cases can be confirmed as simulated refunds. Repeated confirmation does not create additional refund events. No payment provider is connected.
6. Saved applications can be reopened after refreshing or restarting the server.

The date defaults to today. Orders in the current sample data were purchased in August 2026 or earlier; the current date may put them outside the return window. Entering 2026-08-15 is an explicit historical demonstration, not a change to order records.

## Storage and scope

Uploaded images and application histories live in `.local_refund/`, excluded from Git. The server binds to 127.0.0.1 and serves only the UI and defined application endpoints, not the repository directory. Same-origin checks reject cross-origin requests. This is a single-user local prototype; it has no user authentication, role-based reviewer access or production deployment support. Any person using the local page can use the demonstration reviewer form.

CLIP currently leaves product identity, claim-image consistency and often location unavailable. These remain missing and can lead to human review even for a clear image. Visibility is explicit input, not an automatic prediction. The browser defaults to the existing ML Agent mode, with the existing application thresholds; the Week 8 ML experimental 0.90 threshold is not installed as an application default. A rule mode is available under research settings. No external LLM API is required.

Model errors are returned as errors, not replaced by fake results. The first model load may take time and can require access to download pretrained weights if they are not cached. JPEG/PNG files are limited to 8 MB and 20 megapixels.

## Verification

- Full automated suite: 110 passed, 40 existing dependency deprecation warnings.
- Added checks cover actual image byte handoff, invalid uploads, all workflow outcomes, state restrictions, preserved history, failed inference, persistence, duplicate confirmation, HTTP routing and cross-origin rejection.
- Experiment checks verify frozen results and response hashes, threshold boundaries and test-result overwrite protection; no saved experiment was rerun or replaced.
- Actual JPEG upload through the HTTP endpoint ran image quality, cached CLIP, order/policy checks and the ML Agent. It returned human review with missing product/consistency/location evidence.
- Browser JavaScript passes the Node syntax check. Automated browser launch was blocked by the execution environment; visual layout and browser click acceptance remain a manual check.

Controlled test outcomes are not measurements of CLIP or real-world refund accuracy. QA cases in the staging directory are not copied into the user's project storage.
