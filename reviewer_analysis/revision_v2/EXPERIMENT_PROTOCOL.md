# What to run, freeze and report

This is a proposed additional evaluation protocol, not a record of completed experiments.

## Order and decision gates

1. **Restore measurement first (R1.2; R2.35/40).** Recover original evaluator, full references, aliases, deduplication rules and match pairs. Reconcile all Q4 rows, not only Q73. The v2 common-report evaluator is available as an explicitly NEW measurement protocol when needed. Evaluate all methods with the same extraction/matching view. Native graphs remain separate immutable artifacts.
2. **Edge evidence assessment (R1.3/4/5; R2.28/33/38).** Freeze the source snapshots, then assess the same native edge statements without exposing system confidence. Preserve unsupported/unresolved labels. Report label/evidence coverage. Different snapshot versions and different judges use different output directories. Assessors need time/facility/product/geographic scope, not merely plausible domains.
3. **Human check (R1.1/4/5).** Two independent domain reviewers, a stratified claim/citation sample and full Q61/Q64 edge audit, then adjudication. Separate original independent ratings from final labels. Use page-level evidence, not agreement on familiar domain names. Calibration on enriched samples is conditional unless sampling weights are justified.
4. **Independent executions (R1.5).** Freeze code/prompts/model IDs, start a fresh process per query/run, keep failures and incomplete outputs. Three runs are the proposed minimum operational setting. The native runner supports this but does not enforce hidden-backend token/tool budgets.
5. **Fair architecture comparisons (R1.2; R2.5/37/39).** This step still needs the original local baseline and ablation implementations plus actual provider/tool instrumentation. Do not claim it is solved by the native runner.
6. **Test independence (R1.1).** Document an untouched existing test, or create a genuinely new set after freezing everything. Neither a retrospective split nor a `new_holdout` flag proves independence.

## Required matched experiment (not implemented by a placebo flag)

Use the *same available model* for every role and method; use the original ReAct and ToT implementations, original uniform-planning KG control, and Helicase. Same search/page tools, geography/language, maximum generated tokens, maximum actual search/page calls, context/output constraints and prompt freeze. Save actual returned usage (including reasoning tokens as reported), all attempts/retries, page calls, search calls and timestamps. Count every parallel inner query, not only outer worker actions. Stop at the budget before dispatch; report cost of failed and partial calls.

Start with the full 20 Q4 queries × four methods × three runs = **240 executions** as the targeted architectural test. Extend to all quadrants if the revised claim requires general benchmark-wide matched superiority. The count is a proposed design, not evidence that four runners are already connected. Budget caps must be chosen on a documented development pilot, then frozen; do not tune on Q4 test results or choose each system's best budget separately.

Replay/cached-evidence experiments and live-search experiments answer different questions. A shared immutable retrieval cache can reduce temporal drift, but should not be called independent live-search repetitions. Randomise/interleave system order to reduce temporal confounding. Never average new live runs with historical ones without recording the changed environment.

For the no-UQ planning control, verify that score information is absent from planning prompts, prioritisation and target selection as specified. Constant numeric action priority alone may leave UQ information in graph summaries, histories, retrieval breadth or stopping. State exactly what remains. Keep the graph construction and tools; do not give an unrelated new method the old ablation name.

## Reporting boundaries

- Keep fixed and adaptive ECE definitions, binning/tie policy, Brier, coverage and query-cluster CIs together.
- Source-domain diversity is a descriptive statistic, not an independence test.
- Graph F1 evaluates the declared reference relation set; separate it from open-world correctness and citation entailment.
- Direct no-web model answers are parametric-recall references, not evidence-matched controls.
- A reference URL attached to a fact is not a valid citation-support label.
- Do not relabel citation absence as factual contradiction.
- Expert ratings must be performed by experts; the supplied model judge never produces human IAA.
- Model availability, API authentication, live backend compatibility and matched resource instrumentation must be verified on the user's runtime before paid batch execution.
