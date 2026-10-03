# Complementary evaluation protocol: preserve the task, expose the measurements

Version `complementary-evaluation-v1`, 2026-10-03. This supersedes the previous instruction to make complete reference-graph reconstruction the default next task. It is a plan, not evidence that new experiments or manuscript edits are complete.

## Agreed scope

SCQA supplies original questions and prose answers. Preserve them and the archived reports/native graphs. Retain the historical **composite proxy** with its actual formula and limitations; add independent claim/citation assessment. A complete ground-truth supply-chain graph is not a prerequisite for these scoped evaluations. This does not make density a measure of relation truth or remove implementation/record anomalies.

Source basis: [recovered metric](OLD_Q4_METRIC_ZH.md), [historical source snapshot](reproducibility/historical_q4_metric_20261003/eval_scpqa.py), [recorded executions](VALIDATION.md). New design choices below are proposed protocols, not reconstructed facts about the old experiment.

## Work packages and stop gates

| ID | Work | Execution boundary |
|---|---|---|
| O0 | Immutable input manifest; investigate all invalid/empty/version-mismatched records | Offline; do not clip, silently omit or invent missing outputs |
| O1 | Separate answer score, graph-ratio branch and composite contribution | Offline formula audit; not claim-level validation |
| O2 | Verified question-focused answer units/matches, then answer-only and same-formula recomputed composite | Reuse verified records; otherwise bounded evaluation-only calls across all seven Q4 methods; no agent search |
| O3 | Query-paired inference, structural-weight sensitivity and measurement validity checks | Same frozen sample; full sensitivity grid, no winner-based selection |
| N0 | Reuse native-edge evidence, coverage and three-model diagnostics | Completed artifacts stay immutable; conditional results remain conditional |
| N1 | Only missing comparable cross-method answer-claim evidence checks | Fixed sample/snapshot/assessor rules; no whole-graph gold required |
| H1 | Independent human claim/citation checks and published-case edge verification | Real ratings; blinded first, adjudication later |
| B1 | Inventory existing model/budget/run records and ablations | Only identifiable gaps justify further agent runs |

Details, schemas and call estimates: [O0–O3](LEGACY_EVAL_RUNBOOK_ZH.md), [N0–H1](CLAIM_EVIDENCE_PROTOCOL_ZH.md). Current `extract/match` evaluate full-report graphs, not O2 answer units. The answer adapter and cross-method claim preparation are requirements, not implemented new subcommands in this documentation update.

## Fairness without requiring a preferred ranking

Freeze the query set, prose-reference version, task scope and candidate unit rules before reassessment. Extract predictions without reference answers, method names or scores. Retain directly asserted wrong answers; do not silently filter them out. Preserve negation, modality, time, market, facility and product specificity. Normalise aliases and equivalent inverse relations consistently. Distinguish answer relevance from factual support.

Read long reports with declared coverage. Do not penalise an investigation by scoring irrelevant background as missed answer items, but audit additional claims separately. Do not reward long output or native graph existence as correctness. Report the legacy structural branch explicitly and expose answer-only results. No automated source independence assumption follows from distinct domains.

Use identical sampling/evidence policies across comparable methods. No-web answers are parametric-recall references, not evidence-matched controls. Missing citations are missing citations, not automatic factual contradictions. Do not supply one method's newly found evidence to another and claim it was originally cited. Reference-relative unmatched and false are distinct.

All protocol changes have versioned rationales and apply to every affected method. Historical and provisional graph artifacts remain available with scope limitations, including unfavourable results. Do not select judges, seeds, thresholds or reference edits because they restore a desired ranking. A successful low score is not an execution error to retry.

## Agent repetitions and budget controls remain separate

A second evaluation of one report is not a second agent execution. Query bootstrap is not between-run standard deviation. Report mean and sample SD across real independent executions only when those records exist; never fill missing runs from hypothetical worksheets.

Inspect the original no-UQ/uniform-planning, single-agent, ReAct and ToT records first. Reuse valid compatible runs, keeping code, prompts, models, tools, dates, stopping rules and actual resource use. If supporting a causal architecture claim still requires matched experiments, compare the relevant systems with the same available backbone per role, tool access, context/output constraints and predeclared token/tool limits. Count every inner parallel request and failed/retried call. An iteration cap or shared Serper account is not a matched budget.

The existing uniform-planning control is relevant; do not create a duplicate method solely for a new name. Document exactly which uncertainty signals are removed and retained. A constant priority value alone may leave guidance in prompts, targets, search breadth or stopping. Functional ablations are not automatically individual-agent ablations.

Select the smallest task set justified by the revised claim, before seeing its new results. Combining a matched comparison and independent runs avoids two overlapping campaigns. The earlier 20 Q4 × 4 methods × 3 runs = 240 design is an option only if all controls are implemented, budgeted and authorised; **not this batch's default command**. Three runs are an operational proposal, not a magic sufficiency threshold. Historical/live/cached-evidence runs are distinguished and not silently pooled. Randomise/interleave system order where live retrieval is used.

## Remaining reviewer obligations

R1.1 still requires honest annotation qualifications, independent rating/adjudication records, temporal/geographic scope and test-development history. A retrospective split cannot become a genuinely untouched test. A flag does not prove independence.

R1.3 permits conservative heuristic interpretation, but facts, redundancy, memory and execution validity must retain different meanings. Correlation/contradiction limitations are stated; no new runtime safeguard is claimed without implementation.

R1.4/1.5 require specific citation support and real expert checks; model agreement does not substitute. Complete-world recall or verified physical movement is not claimed from a connected graph.

## Reporting and completion

Use distinct table columns for historical reported values, verified recomputed composite values, answer-only performance, and evidence support with its own denominator. Never relabel the old number as a newly measured answer or graph F1. Native confidence calibration is conditional on actual binary labels and evidence selection; absent confidence is NA, not fabricated. CI/sample/assessor choices and all planned pairwise comparisons are reported.

Copy [the status template](REMAINING_STATUS_TEMPLATE.md) into a new local private run folder. Completion means the declared inputs, transformations and outputs are traceable and the relevant requirements met, not that the proposed method ranks first. No new results are created by this protocol file, and no publication/acceptance outcome is guaranteed.
