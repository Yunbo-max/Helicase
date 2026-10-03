# GPT-5.5 Q4 budget-controlled planning experiment

**Goal:** Compare uncertainty-guided Helicase with uniform target selection while retaining KG construction, search, evidence, history and citations in both arms.

**Authority:** The user's 2026-10-04 experiment specification is the approved scope. Implement directly in an isolated worktree; do not add methods or Q3.

**Architecture:** Add experiment-specific controls alongside the existing revision suite. Preserve existing `repeat` behavior and local runtime modifications. Instrument the actual LLM/search/page dispatch boundaries before claiming hard budget matching.

**Global constraints:** GPT-5.5 for every model role; 4 technical pilots (Q61/Q73, both arms), then freeze shared caps from usage before 80 fresh runs (Q61–Q80, two arms, two repeats). No pilot scores in formal results. No reference reaches the research agent. No successful-output reuse or silent failure reruns.

## Implementation sequence

- [x] `planning_budget.py`: thread-safe token reservations, protected final allowance, durable attempt accounting, fail-closed unknown usage. Test concurrent requests, retries, late/invalid usage, and final-phase transitions. Component only; dispatch integration remains below.
- [x] `planning_control.py`: independent target selector, metadata-free graph/history projection, and paired randomized schedule. Test that changing UQ values/order cannot affect uniform input/selection, raw factual qualifiers survive, completed goals are excluded, and every formal query has two paired repeats. Component only; native prompt integration remains below.
- [ ] Actual backend adapter: verify GPT-5.5 access, exact input accounting and provider-enforced output bounds including reasoning. Disable hidden retries; ledger every attempt. Codex CLI post-call usage alone is insufficient evidence of hard caps.
- [ ] Runtime integration: shared neutral candidate generation, one selected investigation target followed by KG integration; Full ranks with existing estimated UQ reduction/cost, Uniform samples distinct valid targets uniformly. Keep UQ computation in both arms, hide it from uniform selection. Fix retrieval parallelism by bypassing `_decide_n`, replace UQ stopping in both arms with identical limits/no-valid-candidate stopping, and handle errors separately. Disable optional non-GPT OCR in both arms.
- [ ] Instrument actual Serper attempts and every page-fetch fallback before dispatch. Count failures/retries. Validate no network/model bypass remains, including generated coding actions. Fresh subprocesses isolate graph/history/caches.
- [ ] Run four pilots, inspect completeness and resource usage only, freeze configuration/source hashes/model identity and schedule. Token/search/page cap values remain unset until pilot evidence exists; pilots themselves require explicit finite safety caps.
- [ ] Execute 80 jobs; save failures, partial answers and budget ledger. Score uniformly against `scpqa.jsonl` with frozen extraction/matching protocol; archive judge usage separately from agent budget.
- [ ] Produce P/R/F1 and resources, query-level paired bootstrap (mean each query's two repeats first), both repeat means and sample SD. Do not condition metric choice on ranking.

The pure `planning_statistics.py` component and its tests are implemented. It requires all 80 scored records, retains failure statuses, and rejects pilot/mixed rows; actual scoring and resource-table integration are not implemented in this change.

## Review focus

1. Concurrent requests cannot consume final-answer reserve or overshoot ceilings.
2. Missing usage/timeouts cannot turn billable attempts into zero-cost retries.
3. UQ-derived ordering, markers and history suggestions cannot leak into uniform planning.
4. Multiple candidate descriptions for one target cannot increase its uniform selection probability.
5. API success is not experiment success: incomplete jobs and unusable outputs remain in the denominator.

## Current preflight

2026-10-04: existing GPT-5.5 Codex path records post-call usage, but hard output caps and hidden retry accounting are unverified. `OPENAI_API_KEY` was empty/unset in inspected project configuration. No new paid calls or experiment jobs have been run. Search/Jina key presence does not establish validity. Runtime adapter and dispatch integration remain required, even after credentials are configured.
