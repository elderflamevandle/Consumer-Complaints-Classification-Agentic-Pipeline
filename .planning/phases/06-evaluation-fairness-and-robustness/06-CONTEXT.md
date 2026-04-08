# Phase 6: Evaluation, Fairness, and Robustness - Context

**Gathered:** 2026-04-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Quantify classifier quality on the held-out set, compute fairness signals for a small set of complaint groups, and harden the demo against critical input/fallback failures. This phase proves reliability and responsible-AI behavior for the existing system; it does not add new product capabilities.

</domain>

<decisions>
## Implementation Decisions

### Reliability priorities and failure semantics
- Prioritize hardening the existing pipeline against input edge cases first: empty complaints, ambiguous complaints, and very long complaints.
- Non-critical fallback behavior should remain non-blocking during a run, but it must be visible to the operator as a warning rather than hidden silently.
- Robustness evidence should live primarily in automated tests and generated evaluation/report artifacts rather than new dashboard surfaces.
- For repeated demo runs, a critical failure means the pipeline crashes or fails to produce final output artifacts; warnings, visible degradations, and successful fallback hops do not count as critical failures by themselves.

### Fairness comparison policy
- Start fairness reporting with product-level complaint groups rather than issue-level or state-level comparisons.
- Use a small fixed shortlist of sufficiently represented groups rather than selecting a new comparison set each run.
- If a group is too small for a reliable ratio, skip it and mark it clearly with a warning instead of forcing it into the report.
- Fairness ratios should use one explicit named baseline group so results stay stable and easy to explain across runs.

### Evaluation reporting contract
- Replace the placeholder `eval` task with a real repeatable repo command that runs the held-out evaluation and saves artifacts.
- The main report should emphasize macro F1 plus a class-level breakdown rather than a single headline score alone.
- Include a small fixed set of failure examples so the evaluation is interpretable in demo and teammate review contexts.
- Do not expand the Streamlit dashboard in Phase 6 just to surface offline evaluation metrics; keep evaluation primarily as a task/report workflow.

### Claude's Discretion
- Exact artifact filenames, folder layout, and report formatting for evaluation outputs.
- Exact fixed product shortlist and named baseline group, as long as they are explicit, well-supported by the holdout split, and stable across runs.
- Exact warning wording and presentation for fallback/degraded behavior using the existing telemetry and audit patterns.
- Exact coverage split between reliability-focused pytest suites and report-generation scripts, provided the locked priorities above are preserved.

</decisions>

<specifics>
## Specific Ideas

- Phase 6 should prove the current system rather than broaden it: reliability first, visibility second, no extra product scope.
- Keep the control-room dashboard focused on live complaint runs; offline benchmarking belongs in repo tasks and saved artifacts.
- Fairness reporting should be simple enough to explain quickly: a few well-supported groups and one stable baseline.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `scripts/build_dataset.py`: already creates deterministic `dev`, `holdout`, and `demos` parquet splits, including the holdout artifact Phase 6 evaluation can consume directly.
- `scripts/tasks.py`: already defines an `eval` task stub, so Phase 6 has a clear entry point to replace rather than inventing a new operator command.
- `src/agents/classifier.py` and `src/schemas/classification.py`: existing strict classifier contract provides the labels and outputs the held-out evaluation must score.
- `src/intake/pipeline.py`: current intake path is the right place to exercise empty/ambiguous/long-input hardening behavior.
- `src/graph/routing.py` and `src/graph/interrupts.py`: existing deterministic routing and same-thread review flows define the graph transitions reliability tests should protect.
- `src/llm/client.py` and `src/llm/rate_limiter.py`: existing retry, fallback, and degrade behavior already provide the non-critical fallback signals this phase should verify and surface consistently.
- `src/ui/runtime.py` and `app/streamlit_app.py`: current dashboard already exposes live telemetry, audit, and budget information, which is enough context for warning visibility without turning the UI into an offline benchmark console.
- `tests/test_llm_client.py`, `tests/test_routing_interrupts.py`, and related pipeline tests: existing focused regression suites provide the pattern for adding Phase 6 reliability coverage.

### Established Patterns
- The repo favors deterministic, task-runner-based workflows over ad hoc notebook-only analysis.
- Safety- and reliability-critical behavior is protected with focused pytest suites rather than relying on manual QA.
- The Streamlit app is a control room for live runs, while offline quality evidence belongs in scripts and artifacts.
- Audit and telemetry layers are already the source of truth for warnings and degraded-path visibility.

### Integration Points
- Held-out evaluation should plug into the processed dataset artifacts under `data/processed` and the existing `eval` task path.
- Fairness metrics should be generated from the same evaluation data flow so the report tells one consistent quality story.
- Reliability tests should extend the current pytest suites around intake, routing, fallback behavior, and graph continuity instead of introducing a separate testing framework.
- Any operator-facing fallback warning should reuse the existing telemetry/audit vocabulary rather than adding a new pause or review mode.

</code_context>

<deferred>
## Deferred Ideas

None - discussion stayed within phase scope.

</deferred>

---

*Phase: 06-evaluation-fairness-and-robustness*
*Context gathered: 2026-04-08*
