# Validation record — software, not new paper experiments

## Provisional Q4 graph matching — 2026-10-03 (Europe/London)

- [Public report, numeric results and execution snapshots](reproducibility/provisional_graph_matching_20261003/README_ZH.md): 140/140 results, seven methods × 20 queries. These use AI-reviewed prose-reference drafts, **not author-confirmed complete gold**.
- Reference preparation: 20 GPT-5.5 CLI calls; 435 nodes, 496 edges; 148 logged offline edits, including quotation context expansions. Original prose and predictions were unchanged. Author confirmation remains absent.
- Matching: 140 initial GPT-5.5 CLI calls plus four structural-validation repairs (DeepSeek 2, Helicase 1, Qwen3-235B 1). Original invalid responses remain retained locally; successful outputs were not rejudged. All 144 traces, exact prompts, token records, one-to-one directed pairs and scores were audited. No failed query was silently excluded.
- Helicase provisional macro Graph F1: 0.2097204611. All six paired mean-difference bootstrap 95% intervals include zero. The result does not establish a clear Helicase advantage. Graph F1 uses 0.6 entity F1 + 0.4 relation F1; 2,000 query bootstrap resamples, seed 20261003, conditional on a fixed reference and matcher.
- The related local suite passed **88 tests in 3.87s**. The publication checkout passed **108 tests, 1 skipped in 3.36s** over the public revision tests and both reproducibility releases, using disabled plugin autoload and `-p no:capture`. The existing skip needs the unpublished primary batch driver.
- All 140 public CSV rows were independently recomputed and checked against summary means. Eight execution scripts and seven numeric/report artifacts were copied byte-for-byte; provenance hashes are published. Raw references, graphs, match-pair mappings, model outputs/account traces, author forms and credentials remain local. These snapshots require private inputs and original path layouts; they are not a turnkey reproduction release.
- No extraction, source retrieval, primary fact judging or agent repeats were restarted. Formal author-confirmed reference evaluation, independent human ratings and strict-budget repeated agent experiments remain outstanding. No 240-run job was launched.


## Three-model frozen-sample evaluation — 2026-10-03 (Europe/London)

- Public aggregate results and byte-identical execution snapshots: [model diversity release](reproducibility/model_diversity_20261003/README_ZH.md). Raw source text, per-fact labels, model responses, account traces and credentials remain private.
- Frozen primary-label-enriched sample: 85 supported, 2 contradicted, 113 of 921 unresolved; seed 20261002. Same prompt and source payloads were replayed. These are sample diagnostics, not population estimates.
- Added requested model IDs `gpt-5.6-sol` and `gpt-5.6-terra`, medium reasoning. Each completed 200 records: 189 successful CLI invocations and 11 zero-call no-evidence unresolved records. Each passed a two-call pilot before continuation. An earlier `gpt-6-sol` attempt was rejected by the account route and is not counted as a judgment.
- Among the 189 actual three-model assessments: 150 unanimous (79.37%), 38 two-agree/one-different, 1 all-different; 39 total disagreements. Pairwise agreement: GPT-5.5/Sol 169/189, GPT-5.5/Terra 157/189, Sol/Terra 162/189.
- The models are from the same provider; no independent training lineage, human validation, or server model snapshot is attested. No majority labels replaced original labels. CLI invocation/token records are not measured HTTP counts or billing statements.
- Offline audits passed for exact prompts, original evidence, unique calls and retained outputs. All 1,542 prior sample/secondary-run artifacts, 1,008 primary items and nine protected original files kept their hashes.
- The private full suite passed **110 tests in 4.41s**. The publication checkout independently passed **101 tests, 1 skipped in 3.76s** using `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q -p no:capture reviewer_analysis/revision_v2/tests reviewer_analysis/revision_v2/reproducibility/model_diversity_20261003`. The skip requires the unpublished private primary batch driver; eight legacy GPT6 transport tests also remain local.
- Public snapshots retain the actual local execution assumptions, including required private manifests and an original-machine hash file. They are not a turnkey dataset release or a new instruction to rerun completed jobs. Public aggregate JSON excludes per-fact identifiers and full source/response text.

Author-confirmed reference graphs, real expert ratings and repeated/strict-budget agent experiments remain outstanding. No 240-run job was launched.

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
