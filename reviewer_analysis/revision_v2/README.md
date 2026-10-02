# Helicase revision tools v2 — continue from the completed evaluation

**Start here: [只做剩余任务 / Remaining tasks](README_ZH.md).**

[Full command reference, preserved](README_FULL_ZH.md) · [Recorded validation](VALIDATION.md) · [Evaluation protocol](EXPERIMENT_PROTOCOL.md)

Reuse the original SCQA dataset, original reference graphs and saved outputs. Do not restart completed extraction, page collection or primary-judge assessment.

The validation record at commit `83d7f07` reports 140 completed common-report extractions, 484 retained page outcomes, and 1,008 native-edge labels. Only 87 edges have binary assessments, so the reported ECE/Brier describe that conditional subset, not the full graph. Detailed outputs remain local/private; the record is not a fresh inspection of those outputs.

## Remaining work, in order

| Task | Inputs | New model work |
|---|---|---|
| Q4 matching and paired statistics | Existing 140 extracted graphs + author-confirmed original reference graphs | Up to 140 matching tasks; no new extraction or agent execution |
| Unresolved-label diagnostics | Final primary labels, item payloads and cached pages | None; an offline example is in the remaining-task guide |
| Bounded alternative-judge check | Frozen sample and exactly the same evidence payloads | Suggested cap: 200 sampled facts, after a two-item interface check |
| Human audit / reference documentation | Existing blank forms and author records | Not replaceable by API calls |
| Agent repeats / matched-budget controls | Existing configurations and raw records first | Still unresolved; not automatically launched by this guide |

The Chinese guide gives commands for existing `match`, `paired`, `judge` and `analyse` entry points, completion criteria, and explicit local preparation requirements. Secondary sampling and cross-model agreement preparation are requirements, **not new CLI subcommands**. Do not treat `analyse` as an automatic inter-judge agreement calculation.

```bash
git pull --ff-only origin main
python -m reviewer_analysis.revision_v2 --help
```

For first-time setup only, use the preserved full reference. Do not repeat `prepare` merely because the README changed.

No core algorithm, dataset, original result, primary label, prompt or runtime code is changed by this documentation update. Network-backed commands still require `--execute`. The native runner is serial: `--max-jobs` limits launches, not concurrency. Keep credentials, raw research records, page text and login traces in ignored private directories.
