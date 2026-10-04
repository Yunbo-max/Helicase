# GPT-5.5 Q4 controlled planning experiment

User-approved scope: only Full and Uniform-planning KG, Q61–Q80, two repeats (80 formal executions), preceded by four technical pilots. Preserve KG, search, evidence and history. No reference reaches the research agent.

## Authorized budget amendment

The user explicitly chose the existing Codex GPT-5.5 path with shared model-call and tool ceilings. Tokens are measured only, not strictly matched. Model ceilings count CLI invocations; internal HTTP attempts are not independently attested. Retrieval ceilings count actual HTTP attempts before dispatch.

## Implementation and execution

- [x] Thread-safe model invocation ledger with final-answer reserve and explicit unknown usage.
- [x] Neutral shared candidate generation; Full uses original UQ gain/cost, Uniform samples distinct targets. Shared fixed n=2 and UQ-independent stopping.
- [x] Actual Serper/page transport accounting including failure, retry and redirect; shared disabled OCR/browser fallback.
- [x] Frozen source snapshots, questions-only input, fresh workers, paired randomized 4/80 schedules, explicit failures.
- [x] New-report extraction, normalization and matching with frozen scpqa V4 references; usage separate from agent execution; per-query paired statistics.
- [x] Software verification: 223 passed, 3 skipped; separate native synthetic integration: 2 passed. Real GPT-5.5 and updated Serper preflight succeeded.
- [ ] Complete four technical pilots and inspect functionality/usage, without judging rankings.
- [ ] Freeze shared caps using 1.25 times maximum observed pilot use, rounded upward to multiples of five, with documented minimums.
- [ ] Complete 80 fresh formal executions, preserving failed/partial outputs.
- [ ] Evaluate all outputs, publish P/R/F1, query-level paired CI, repeat means/SD and actual resources.

Four pilots have started in private/planning_gpt55_v1; formal execution has not started. Source hashes are frozen. Changes requiring a revised implementation must create a new experiment version, not silently replace already run records. See PLANNING_RUNBOOK_ZH.md and BUDGET_PLANNING_STATUS_ZH.md.
