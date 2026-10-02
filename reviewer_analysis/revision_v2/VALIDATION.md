# Validation record — software, not new paper experiments

- Full added-tool test suite: **46 passed** (`python -m pytest -q`).
- Python compilation check: passed.
- Actual uploaded archive: 7 methods × 80 = 560 input records imported.
- Native fact records imported: 8809.
- Helicase Q4 raw edges: 1,008; 992 with reference IDs; 969 resolving at least one saved HTTP(S) URL.
- Invalid archived metric entries flagged (not clipped): 8.
- Q4 common-report extraction dry run: 140 tasks; no network requests.
- Cited-page dry run for native Helicase Q4 edges: 484 unique URLs; no requests.
- 400 blind audit rows generated, with blank independent ratings. Agreement correctly remains undefined with zero completed rating pairs.
- Fresh-process supervisor: tested against a **synthetic local runtime**, not the missing real backend.
- LLM client resume and quote-validation paths: tested with **mocked responses**, not paid API calls.
- Calibration CSV/LaTeX/PNG/SVG rendering: smoke-tested using **synthetic labels only**, not SCQA labels.
- Real `helix_core` was not available; no real agent runs, no human annotations and no API-key/model-availability tests were performed.
- Publication adds only this tooling directory. It does not upload the private runtime, raw archive, credentials, or new experimental results. Remote publication is verified separately against Git blob hashes and the branch head.

The earlier grouped calibration claims are not reused. Exact numerical metrics from correctly paired labels still depend on the validity, scope and selection of those labels. Source support judged by an LLM is not certified world truth or independent expert validation.

Archive SHA-256: `6390435358ece6d810315ae41036d89881f2ca9433bbe9d8d1fb1729cf65d58c`.
