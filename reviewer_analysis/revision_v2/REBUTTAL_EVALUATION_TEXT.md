# Evaluation positioning and reviewer responses — working text

Manuscript ID: 268226721. Version `complementary-evaluation-v1`.

**This file updates the response strategy, not the online Google Doc or paper/main.tex.** Present-tense statements below describe recovered code or publicly recorded evaluations. Future-tense changes are not completed experiments. Before submission, reconcile every claim, result and page/line location with the actually revised manuscript. Do not use the unrelated TabKG response as Helicase content.

## Core positioning

> SCQA evaluates query-specific supply-chain investigation using textual reference answers. We retain the original questions, references and system outputs. The legacy Q4 computation combines answer-fragment semantic agreement with a native edge-to-node-ratio adjustment. It is a custom composite proxy, not direct relation-level precision and recall. We distinguish this composite score from its answer-matching component and from a complementary assessment of claim-level citation support. These measurements answer different questions and do not require an exhaustive ground-truth supply-chain graph.

This is not a claim that the proxy is empirically validated as a measure of factual relation quality. Its structural branch and known invalid historical rows must remain explicit. New evidence assessment complements the chosen task measure; it does not repair invalid counts by itself.

## R1.1 — reference validity and completeness

**Response:**

> Thank you for asking us to clarify the reference scope. The available SCQA references are textual answers, rather than an exhaustive annotation of every entity and relationship that an investigation might discover. We distinguish whether a statement is represented in the reference from whether it is supported by evidence. Converting a prose answer into a graph introduces further choices about entity granularity, relation representation and background content. We therefore do not treat an automatically converted graph as complete world ground truth.
>
> We will retain the original SCQA questions and textual references, document their annotation and scope, and separate reference-based answer matching from evidence assessment. This does not remove the need to substantiate annotator qualifications, adjudication, agreement and test independence. Those details will be reported from the actual records rather than inferred from score summaries.

**Changes in the manuscript:** Planned: clarify textual-reference scope in Dataset, replace claims of an already complete gold graph, and document time/market/product/facility limits and annotation history. Verification required: actual annotation/held-out records. No new dataset or independent test is claimed here.

## R1.2; R2.35/37/40 — score definition, narratives and fairness

**Response:**

> The recovered evaluator makes the legacy computation explicit. It first matches fragments of a concise answer against the textual reference. It then constructs a relation-quality proxy from the answer scores and native graph statistics. It does not directly compare predicted relations with annotated reference relations. We therefore distinguish the retained composite proxy from relation accuracy and will report the answer-only component separately.
>
> This decomposition also exposes the different structural branches for outputs with and without a native graph. We will check invalid or inconsistent records and report any recomputed scores as a new evaluation version, preserving the original records. Complementary claim-level assessment will examine whether the reported relationships have source support, without requiring narratives to reproduce an arbitrarily specified full graph.
>
> Shared search tools are distinct from matched computational budgets. We continue to distinguish no-web model references from search-enabled systems. The original uniform-planning control is the relevant no-guidance comparison; its actual configuration and run records, not its name alone, determine what it isolates. The scoring clarification is not presented as resolving the separate matched-budget request.

**Changes in the manuscript:** Planned: state the actual legacy formula and native/no-native branches in Evaluation; label it as a composite proxy; present answer and structural components separately; distinguish comparable output views; reconcile invalid rows and associated table/ablation claims. The procedure is now located, so remove stale statements that no evaluator has been found. Historical model identity still needs run configuration, and score/algorithm changes must not be described as unchanged reruns.

## R1.3; R2.28/33/38 — uncertainty and complementary evidence

**Response:**

> We distinguish the legacy query-level discrepancy from fact-level calibration. The former compares one minus final memory score with the legacy composite result. It does not evaluate confidence against independently labelled graph facts. Evidence-consistency, trajectory-redundancy and memory-control signals are interpreted as operational heuristics rather than assumed calibrated probabilities.
>
> The additional archived-output assessment has recorded 1,008 native-edge judgments against supplied source excerpts: 85 supported, two contradicted and 921 unresolved. Conditional calibration was computed for 87 binary-assessed edges, corresponding to 8.63% coverage across 15 queries. The recorded Brier score is 0.052989 and ECE is 0.157471. These are conditional, LLM-assessed support diagnostics, not full-graph accuracy or independent human calibration. Unresolved labels are not treated as false.
>
> The complementary evaluation makes the source-support question explicit. We will report coverage and limitations alongside the scores, including the effects of correlated evidence and missing or truncated source material. Neither density nor agreement is used as proof of truth or statistical independence.

**Changes in the manuscript:** Proposed integration of already recorded diagnostics: separate query-level legacy discrepancy from native-fact support calibration; state assessor, confidence origin, coverage, binning and query-cluster intervals; remove the obsolete claim that no new fact labels have been generated. Retain source-dependence/memory-dilution limitations and do not claim unimplemented contradiction safeguards.

## R1.4; R2.18/21 — specific claims, not exhaustive graph reconstruction

**Response:**

> We agree that a connected path does not establish physical material flow. Our evaluation separates a reported relationship, a candidate or inferred relationship, production capability, and a claim of actual flow. A company-level contract does not establish that material entered a particular product. These distinctions can be checked at the claim level without enumerating a complete supply-chain graph.
>
> We will use the saved source material for a scoped review of substantive case-study relationships and a fixed sample of answer claims. Each judgment will be linked to the relevant passage and its product, time, geographic and facility scope. Reference presence, URL availability and citation support will be reported separately. Independent expert review remains necessary before describing case relationships as verified.

**Changes in the manuscript:** Planned: add the claim/evidence protocol, preserve tentative/negative/planned status, provide source-specific case ledgers, and remove physical-trace interpretations not justified by evidence. No blanket assertion is made that every runtime edge already has verified metadata. Cross-method support claims require a comparable sample; Helicase-native diagnostics alone do not establish superiority.

## R1.5 — judge variation, humans and repeated executions

**Response:**

> An additional frozen-sample comparison has been recorded for three requested model configurations. The sample contains all 87 primary binary-assessed facts and 113 sampled unresolved facts. Of 200 records, 189 were actually assessed by all three models; 11 had no usable evidence and were marked unresolved without a model call. On the 189 model-assessed records, 150 judgments were unanimous and 39 differed. Pairwise agreements were 169/189, 157/189 and 162/189.
>
> These are descriptive results for a primary-label-enriched sample. They are not population agreement estimates, independent expert validation, or proof of independent model training lineages. The recorded requests are GPT-5.5, GPT-5.6-Sol and GPT-5.6-Terra; the CLI did not attest service-side snapshots. Original labels were not replaced by majority votes.
>
> Judge sensitivity, query-sampling intervals and variability between agent executions are different. The completed judge comparison does not satisfy the request for independent agent runs. We will report actual independent human ratings and compatible execution records where available, with any remaining requirements stated separately.

**Changes in the manuscript:** Proposed integration of recorded three-model diagnostics with sample/denominator limitations; update stale alternative-Judge pending text. Human forms are not completed ratings, and query bootstrap is not run-level SD. Existing no-UQ/budget/repeat records must be reviewed before launching only the missing controls.

## Placement and wording guardrails

- Main task results may retain a validated/recomputed composite column, alongside answer-only scores, with explicit formula and limitations. Historical defective rows remain in the audit trail, not certified unchanged in a headline mean.
- Evidence support and conditional calibration belong in a separate table with their denominators. Do not merge them numerically with the composite to select the best ranking.
- The provisional full-report graph evaluation remains documented, including its low scores and known extraction issues. It is not silently deleted or retroactively called the original task.
- “Changes in the manuscript” above lists intended edits or integration of recorded results. Change to “we have revised/reported” only after the manuscript is actually updated; replace section/page placeholders with verified final locations.
- No wording guarantees that reviewers will accept the scope reduction. Annotation, human validation, budget and genuine repeat-run requests remain separately accountable.

Sources: [legacy definition](OLD_Q4_METRIC_ZH.md), [code/provenance](reproducibility/historical_q4_metric_20261003/provenance.json), [completed runs](VALIDATION.md), [model comparison](reproducibility/model_diversity_20261003/README_ZH.md). New sample designs and future operations are specified in [the claim protocol](CLAIM_EVIDENCE_PROTOCOL_ZH.md), not claimed as already executed.
