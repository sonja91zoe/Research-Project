# Local SQLite refund workflow

## Update: retained photos

New assessments retain exact uploaded image bytes in the `evidence_images` SQLite table, deduplicated by SHA256 and linked from each assessment. The photo and record are committed in one transaction. `image()` verifies integrity on retrieval. Earlier imported assessments without images remain explicitly unavailable; no guessed historical association is added. The local UI provides a saved-photo history expander. Backend tests verify byte-identical image retrieval after reinstantiating the service.

Run from the repository root:

```sh
REFUND_LOCAL_CASE_DB="$PWD/artifacts/local_refund/cases.db" HF_HOME="$PWD/artifacts/model_cache" .venv/bin/python -m streamlit run cloud_pilot/refund_app.py --server.address 127.0.0.1 --server.port 8503 --server.headless true
```

This is an opt-in single-user local mode. Do not set REFUND_LOCAL_CASE_DB on a public deployment without authentication and per-user access controls. Default cloud/session behavior is unchanged.

Install the project dependencies in your own virtual environment first. CLIP requires an initial model download; only set HF_HUB_OFFLINE=1 and TRANSFORMERS_OFFLINE=1 after the model is cached. Model caches, external photos, and local databases are not included in this delivery.

Tables: orders (copied synthetic order records), refund_cases (current case inputs), workflow_records (full JSON assessments, input snapshots, corrections, reviewer actions and simulated refund events), evidence_images (uploaded image bytes). Writes are transactional and stale updates are rejected. A fresh checkout creates its own database; local demo cases are not shipped. Historical inputs inside imported assessments depend on what the original version captured.

Purchase date verification rejects invalid or mismatching dates and requests before purchase/delivery. It is not a real-transaction verification or a refund-policy window determination. Corrections require a new upload and fresh assessment, preserve old history, and invalidate prior approval. Closed cases cannot be amended.

28 related automated tests passed (controlled workflow tests, not model accuracy). Reinstantiating the service verifies database recovery after restart. Local browser checks covered rejecting a mismatched purchase date, accepting the corrected date, correcting a description, reanalysis, and displaying both retained photos. No public deployment verification is claimed.

Run tests: `.venv/bin/python -m pytest cloud_pilot/test_persistent_workflow.py cloud_pilot/test_corrections.py cloud_pilot/test_workflow.py cloud_pilot/test_core.py tests/test_order_database.py -q`.
