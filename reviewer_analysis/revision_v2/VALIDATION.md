# Validation record — software, not new paper experiments

## Local Q4 archive evaluation — 2026-10-02

- Software suite: **81 passed** (`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q -p no:capture`). The clean public package was separately verified: **80 passed, 1 skipped**; the skipped case requires the intentionally unpublished private batch driver.
- Requested evaluator: `gpt-5.5`, medium reasoning, using the existing Codex/ChatGPT login. No server model snapshot is attested by the CLI.
- Common report extraction: **140/140** validated graphs. First pass accepted 125; separate quote repairs and one exact-triple deduplication recovered the other 15. Original outputs, changes and edge aliases are retained.
- Citation collection: all **484** URLs have retained outcomes; **426** usable after access-denial screening, 58 failed or blocked.
- Native Helicase Q4 evidence judgments: **1,008/1,008**; 85 supported, 2 contradicted, 921 unresolved. These are current-excerpt LLM assessments, not human truth labels.
- Conditional calibration: 87 binary-assessed edges (**8.63% coverage**, 15 queries). Brier 0.052989; ECE 0.157471. Query-cluster bootstrap uses 2,000 resamples; full-population algebraic bounds are reported separately.
- Integrity audit revalidated all 1,008 labels, 484 page outcomes and **1,081 completed CLI invocation records**, including extraction repairs. One reconnect event followed by a complete answer was recovered after explicit inspection; its original rejection remains on disk. CLI internal attempts and billing are not independently attested.
- All nine protected original core/archive files retain their initial hashes.
- Human materials: 400 blank independent rating forms with 324 linked source snapshots. No human ratings were fabricated.
- JSON, CSV, LaTeX, SVG/PDF/PNG figures, original traces and a Chinese completion report are saved locally under the ignored private output directory.

**The full research goal remains incomplete:** graph F1 requires author-confirmed reference graphs; human agreement requires real independent ratings; original-agent repeats, n=1 and strict four-system token/tool-budget experiments have not run; held-out provenance remains missing. No 240-run job was launched, and no local results were published by this execution.

## Original upstream tooling validation

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
