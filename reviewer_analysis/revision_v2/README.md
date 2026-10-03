# Helicase revision: retained composite proxy + complementary evidence evaluation

Protocol `complementary-evaluation-v1` (2026-10-03), grounded in repository revision `ccad149`.

**Keep the original SCQA questions, prose references, reports, native graphs and historical scores. Retain the legacy composite proxy with its actual definition. Add claim-level evidence evaluation; do not require an exhaustive gold graph to evaluate the original question-answering task.** This does not validate the proxy as relation accuracy or waive known counting errors.

Start with the [Chinese remaining-work guide](README_ZH.md).

| Document | Purpose |
|---|---|
| [Legacy runbook](LEGACY_EVAL_RUNBOOK_ZH.md) | Exact formula, offline decomposition, bounded answer reassessment, validity tests and call accounting |
| [Claim/evidence protocol](CLAIM_EVIDENCE_PROTOCOL_ZH.md) | Comparable answer claims, source support, coverage, conditional calibration and human checks |
| [Rebuttal text](REBUTTAL_EVALUATION_TEXT.md) | Author-facing wording, reviewer mapping and manuscript changes; planned work stays in future tense |
| [Experiment protocol](EXPERIMENT_PROTOCOL.md) | Frozen inputs, fair scoring, budget and repeat-run boundaries |
| [Status template](REMAINING_STATUS_TEMPLATE.md) | Separate completed/reused results from planned, blocked and unrun work |
| [Historical metric explanation](OLD_Q4_METRIC_ZH.md) | Preserved source audit; not a new validation of old rankings |
| [Validation record](VALIDATION.md) | Previously reported executions, not tests rerun by this documentation change |

Completed common-graph extraction, provisional matching, source retrieval and native-edge multi-judge diagnostics are not restarted. The provisional graph result and its limitations remain available; they are not erased because of the ranking. Native-edge labels do not automatically validate a new answer-level evaluator or a cross-method claim sample.

Current sequence: inspect archived inputs and invalid rows; expose answer and structural components separately; reassess answer units only where reliable matches cannot be recovered; reuse evidence diagnostics; add only missing comparable claim checks and real human ratings. Original-agent repeats and strict matched-budget comparisons remain separate requirements, not an automatic 240-job launch.

```bash
git status --short
git pull --ff-only origin main
python -m reviewer_analysis.revision_v2 --help
```

This update changes documentation only. No algorithm, evaluator, dataset, score, model output, manuscript or credential is changed. No new answer-unit/legacy CLI is implemented here. The existing `extract`/`match` commands evaluate full-report graphs, not the proposed answer-unit view. Implement and test that adapter locally before any bounded model pilot. Existing `judge`, `analyse`, `paired --metric` and `agreement` are reusable subject to their schemas.

[The historical full command guide](README_FULL_ZH.md) is retained for reference, not an instruction to restart completed jobs. Paid operations require `--execute`. The native runner remains serial; `--max-jobs` is a launch limit, not concurrency. Keep raw records and credentials private. Hypothetical personal-draft tables are not empirical runs.
