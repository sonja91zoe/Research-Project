# Streamlit image feasibility pilot

Copy this directory into the project as `cloud_pilot/`.
Run from the project root:

```sh
python -m pip install 'streamlit>=1.40,<2'
python -m streamlit run cloud_pilot/app.py
```

The existing local environment already provides image/model dependencies. The adjacent `requirements.txt` is for the isolated cloud deployment; Linux uses CPU-only PyTorch and headless OpenCV. Do not install headless OpenCV over the existing local OpenCV installation.

Deployment entrypoint: `cloud_pilot/app.py`. Deploy the `student4/streamlit-cloud-pilot` branch after committing and pushing the pilot. Start with Python 3.11 in cloud settings. Cloud installation and inference must be verified; local testing is not proof that the free cloud memory limit is sufficient. Dependency ranges are provisional for feasibility; record and pin the successfully deployed package versions after validation.

Only Members 1 and 2 are exercised. No persisted application history, order/policy verification, refund decision or reviewer action is exposed. This does not yet replace the complete local refund website. The saved Week 6 sklearn model is not loaded.

Success requires `clip_inference_completed: true`. A quality-gate rejection is not a successful CLIP deployment test. First inference can include model download and initialization. The cached CPU model is shared, inference is locked, and concurrent inference attempts ask the caller to retry. User results are session-local; temporary input files are removed after each attempt.

Validation: three controlled tests cover quality gating, actual file handoff/cleanup, invalid images and the busy lock. Real CPU inference is separately smoke-tested with the bundled jacket image in the existing local environment. Streamlit browser rendering and Linux cloud installation remain deployment acceptance checks.
