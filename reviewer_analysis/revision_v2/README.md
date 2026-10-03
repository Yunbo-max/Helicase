# Helicase revision tools v2 — continue from the completed evaluation

**Metric clarification (2026-10-03):** [Historical Q4 formula and source snapshot](OLD_Q4_METRIC_ZH.md). Historical Q4 scores combine concise-answer semantic matching with a native-graph-density relation proxy. The newer full-report graph-matching scores measure a different object and are not directly comparable. Provisional matching is complete; pause new model calls and full agent reruns while auditing alignment offline.

**Start here: [只做剩余任务 / Remaining tasks](README_ZH.md).**

[Full command reference, preserved](README_FULL_ZH.md) · [Recorded validation](VALIDATION.md) · [Evaluation protocol](EXPERIMENT_PROTOCOL.md)

Reuse the original SCQA dataset, original reference graphs and saved outputs. Do not restart completed extraction, page collection or primary-judge assessment.

The validation record at commit `83d7f07` reports 140 completed common-report extractions, 484 retained page outcomes, and 1,008 native-edge labels. Only 87 edges have binary assessments, so the reported ECE/Brier describe that conditional subset, not the full graph. Detailed outputs remain local/private; the record is not a fresh inspection of those outputs.

## Remaining work, in order

| Task | Inputs | New model work |
|---|---|---|
| Offline alignment audit | Original prose, converted reference, extracted reports and actual match pairs | None; provisional matching is already complete (140/140) |
| Scope and representation review | The same 20 queries and seven methods | None; resolve time/market, background facts, granularity and assertion status first |
| Unresolved diagnostics / alternative judges | Completed diagnostics and frozen-sample three-model results | Already completed; do not repeat unchanged inputs |
| Human audit / reference documentation | Existing blank forms and author records | Not replaceable by API calls |
| Agent repeats / matched-budget controls | Existing configurations and raw records first | Still unresolved; paused, not automatically launched |

The Chinese guide gives commands for existing `match`, `paired`, `judge` and `analyse` entry points, completion criteria, and explicit local preparation requirements. The command examples are historical instructions, not authorization to rerun completed tasks. Secondary sampling and cross-model agreement preparation are **not new CLI subcommands**. Do not treat `analyse` as an automatic inter-judge agreement calculation.

```bash
git pull --ff-only origin main
python -m reviewer_analysis.revision_v2 --help
```

For first-time setup only, use the preserved full reference. Do not repeat `prepare` merely because the README changed.

No core algorithm, dataset, original result, primary label, prompt or runtime code is changed by this documentation update. Network-backed commands still require `--execute`. The native runner is serial: `--max-jobs` limits launches, not concurrency. Keep credentials, raw research records, page text and login traces in ignored private directories.
