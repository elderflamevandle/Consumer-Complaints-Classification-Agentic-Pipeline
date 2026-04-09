# Phase 6: Evaluation, Fairness, and Robustness - Research

**Researched:** 2026-04-08
**Domain:** Holdout evaluation, product-group fairness reporting, and reliability hardening for the existing complaint pipeline
**Confidence:** MEDIUM

<user_constraints>
## User Constraints (from 06-CONTEXT.md)

### Locked Decisions
- Phase 6 proves the current system rather than broadening scope.
- Reliability work starts with empty complaints, ambiguous complaints, and very long complaints.
- Non-critical fallback behavior stays non-blocking, but it must be visible to the operator.
- Robustness evidence should live primarily in automated tests and generated report artifacts.
- Fairness reporting starts with product-level complaint groups.
- Fairness uses a small fixed shortlist, skips underpowered groups with warnings, and compares against one named baseline group.
- Evaluation must be a real repeatable repo task, not a placeholder or notebook-only workflow.
- The main evaluation report should center macro F1 plus class breakdowns and include a small fixed set of failure examples.
- Phase 6 should not expand the Streamlit dashboard just to surface offline evaluation metrics.

### Carry-forward Constraints
- The classifier contract remains the strict Phase 2 schema: `product_type`, `issue_type`, `severity`, `compliance_risk`, `confidence`.
- Same-thread review routing and audit logging remain deterministic and must not be redefined.
- Fallback and degrade behavior already live in `src/llm/client.py` and `src/llm/rate_limiter.py`; Phase 6 should verify and surface those behaviors, not replace them.
- The repo prefers deterministic local workflows via `scripts/tasks.py`, pytest, Ruff, and mypy.

### Claude's Discretion
- Exact evaluation artifact directory and file names.
- Exact fixed product shortlist and named baseline, as long as support is adequate and the choice stays stable.
- Exact warning wording and whether fallback visibility is shown through stage artifacts, audit events, or both.
- Exact implementation split between new `src/evaluation/` modules and thin script wrappers.

</user_constraints>

<research_summary>
## Summary

Phase 6 needs a production evaluation layer, not a notebook patchwork.

Recommended strategy:
1. Add a dedicated `src/evaluation/` package with an explicit raw-label normalization layer, because the holdout dataset uses CFPB raw `product` and `issue` strings while the classifier predicts the project's reduced enums.
2. Replace the `eval` task stub with a deterministic holdout runner that reads `data/processed/holdout.parquet`, executes the classifier, computes macro F1 plus per-class metrics, samples a few failures, and writes JSON + Markdown artifacts.
3. Compute fairness in the same evaluation pass over a normalized results frame, using a fixed product-group shortlist, one named baseline group, and explicit warnings for underpowered groups.
4. Keep fairness and evaluation surfacing report-first; do not build a new offline-metrics dashboard view in Phase 6.
5. Use a separate reliability plan to harden empty and long-input behavior and to make non-critical fallback warnings visible through existing runtime telemetry patterns.

Key planning implication:
- The current holdout split is ready to use, but there is no production taxonomy adapter, no evaluation harness, and the repo task runner still prints a placeholder for `eval`. Those gaps have to be addressed before metrics or fairness claims are credible.

</research_summary>

<repo_findings>
## Repo Findings That Matter

### Existing assets
- `data/processed/holdout.parquet` exists with 2,000 rows and columns `id`, `product`, `issue`, `narrative`, `state`, `date`.
- `scripts/build_dataset.py` already enforces deterministic `dev`, `holdout`, and `demos` splits.
- `src/agents/classifier.py` already exposes a strict classification call plus deterministic fallback behavior.
- `scripts/tasks.py` already reserves an `eval` entrypoint, but it is still a stub that prints "Evaluation harness arrives in Phase 6."
- Existing tests already cover classifier fallback, llm degrade behavior, routing interrupts, and intake ambiguity handling.

### Gaps discovered during research
- The holdout dataset carries 17 distinct raw product labels and 86 distinct raw issue labels, while the classifier predicts only 7 product enums and 6 issue enums plus `OTHER`.
- No production module maps raw CFPB labels to the current classifier taxonomy.
- The strongest existing taxonomy work is trapped in `tests/data_exploration.ipynb`; it is not reusable from `src/`.
- The holdout split is dominated by credit-reporting products, so fairness and evaluation reports need explicit handling for class imbalance and baseline selection.
- No existing evaluation artifact format or reporting directory is defined in the repo.

### Planning consequence
- Plan 06-01 must create the normalization contract first. Without that, macro F1 and fairness results will be comparing incompatible label spaces.

</repo_findings>

<standard_stack>
## Standard Stack

### Core
| Library/Module | Purpose | Why it fits this phase |
|----------------|---------|------------------------|
| `pandas` + `pyarrow` | Load holdout parquet and aggregate evaluation data | Already in the repo and sufficient for deterministic offline evaluation |
| `pathlib` + `json` + Markdown writer helpers | Persist evaluation artifacts | Keeps reporting dependency-light and easy to diff |
| `src/agents/classifier.py` | Source of classification predictions | Existing strict schema + fallback behavior must remain the evaluation subject |
| `scripts/tasks.py` | Stable repo entrypoint | Already the project-standard operator command surface |
| `pytest` | Regression coverage for evaluation and reliability | Matches existing repo practice and Phase 6 OPS-02 requirement |

### Supporting
| Library/Pattern | Purpose | Phase use |
|-----------------|---------|-----------|
| `src/evaluation/taxonomy.py` (new) | Raw-label normalization contract | Converts holdout truth labels into project enum space deterministically |
| `src/evaluation/harness.py` (new) | Batch evaluation coordinator | Keeps script logic thin and testable |
| `src/evaluation/fairness.py` (new) | Group selection, baseline comparison, disparity ratio logic | Encapsulates EVAL-02 without coupling fairness math to CLI code |
| `src/evaluation/reporting.py` (new) | Markdown/JSON artifact rendering | Keeps reports deterministic and reviewable |
| existing UI runtime telemetry | Fallback/degrade visibility reuse | Lets reliability work surface warnings without inventing a second operator model |

### Alternatives Considered
| Chosen | Alternative | Tradeoff |
|--------|-------------|----------|
| production `src/evaluation/` package | notebook-only analysis | production package is more setup, but notebook-only output is not repeatable or testable |
| dependency-light metric calculation | adding `scikit-learn` immediately | pure Python + pandas avoids new install friction and is enough for the required metrics |
| report-first fairness surfacing | new Streamlit evaluation page | report-first honors the user's Phase 6 constraint and keeps UI scope contained |
| explicit raw-to-enum mapping | scoring against raw CFPB labels directly | direct raw scoring would be invalid because the classifier taxonomy is reduced and different |

</standard_stack>

<architecture_patterns>
## Architecture Patterns

### Pattern 1: Normalize Truth Labels Before Scoring
- Build a dedicated mapping module that converts raw CFPB `product` and `issue` strings into the project's classifier enums.
- Make the mapping deterministic, testable, and reusable by both the evaluation harness and any later demo-hardening scripts.
- Treat unsupported or ambiguous raw labels as explicit `OTHER`, not ad hoc fallthrough.

### Pattern 2: One Batch Harness, Many Artifact Views
- The batch harness should produce one normalized results frame per run containing:
  - raw complaint metadata
  - normalized truth labels
  - predicted labels
  - confidence
  - fallback/degraded indicators where available
  - error/warning markers
- Macro F1, class breakdowns, fairness ratios, and failure samples should all be derived from that same results frame.

### Pattern 3: Fairness as Group-Performance Comparison, Not New UI
- Because the user chose product groups and report-first surfacing, fairness should be calculated offline and emitted in the evaluation artifacts.
- Use a fixed shortlist plus named baseline group chosen for support and interpretability.
- Underpowered groups should be skipped with explicit warnings rather than padded or silently omitted.

### Pattern 4: Reliability Uses Existing Runtime and Routing Contracts
- Empty/ambiguous/long-input hardening belongs in intake and runtime boundaries, not in a separate reliability facade.
- Non-critical fallback visibility should reuse existing telemetry/audit vocabulary and the current control-room model.
- Reliability tests should extend `tests/test_intake_pipeline.py`, `tests/test_llm_client.py`, `tests/test_routing_interrupts.py`, and focused new Phase 6 tests rather than adding a new testing framework.

### Pattern 5: Report Readability Matters
- The evaluation report should be concise enough for teammate and judge review:
  - one top-line macro F1 section
  - a compact per-class breakdown
  - fairness table for selected groups
  - a small fixed set of sampled failure examples
- Keep the artifact deterministic so repeated runs on the same transport and holdout split are diffable.

</architecture_patterns>

<dont_hand_roll>
## Don't Hand-Roll

| Problem | Avoid | Use Instead |
|---------|-------|-------------|
| invalid metric comparisons | scoring raw CFPB labels directly against classifier enums | explicit taxonomy normalization module |
| non-repeatable evaluation | notebook-only analysis cells | task-runner command + checked-in source modules |
| fairness on thin groups | computing ratios for every group regardless of support | fixed shortlist + support threshold + warnings |
| hidden degraded behavior | relying on model names alone to imply fallback | explicit fallback/degrade warning fields in runtime/report output |
| UI scope creep | building a new dashboard just for offline metrics | CLI/report artifacts and minimal reuse of existing telemetry surfaces |

</dont_hand_roll>

<common_pitfalls>
## Common Pitfalls

### Pitfall 1: Raw-label and model-label spaces are mixed
- **Risk:** macro F1 and fairness metrics are meaningless.
- **Prevent with:** production taxonomy mapping tests before the harness is trusted.

### Pitfall 2: Class imbalance hides poor coverage
- **Risk:** dominant credit-reporting categories swamp the report and weaker groups disappear.
- **Prevent with:** per-class breakdowns, explicit support counts, and a fixed shortlist for fairness.

### Pitfall 3: Fairness is treated like a legal demographic claim
- **Risk:** the demo overstates what Phase 6 proves.
- **Prevent with:** frame the report as group-performance disparity across complaint product groups, not demographic fairness certification.

### Pitfall 4: Evaluation depends on live API variability
- **Risk:** tests become flaky or expensive.
- **Prevent with:** keep harness/regression tests transport-driven and deterministic; reserve live runs for optional manual checks.

### Pitfall 5: Reliability changes silently alter routing behavior
- **Risk:** Phase 6 hardening breaks same-thread review or fallback semantics from earlier phases.
- **Prevent with:** extend existing routing and llm-client regression suites instead of writing standalone smoke tests only.

</common_pitfalls>

<code_examples>
## Code Examples

### Taxonomy adapter sketch
```python
truth = normalize_truth_labels(
    raw_product=row["product"],
    raw_issue=row["issue"],
)
assert truth.product_type in ProductType
assert truth.issue_type in IssueType
```

### Batch harness sketch
```python
result = run_holdout_evaluation(
    dataset_path=Path("data/processed/holdout.parquet"),
    sample_failures=5,
)
assert result.macro_f1 >= 0.0
assert result.class_rows
```

### Fairness report sketch
```python
fairness = build_fairness_report(
    evaluation_rows=rows,
    group_field="truth_product_group",
    baseline_group="CREDIT_CARD",
)
assert fairness.skipped_groups or fairness.comparisons
```

</code_examples>

<sota_updates>
## State of the Art (2025-2026)

- For this repo, the lowest-risk Phase 6 path is still deterministic offline evaluation with checked-in code, not hosted dashboards or notebook-first reporting.
- Group-performance disparity reporting is acceptable as a demo-grade fairness signal when the report clearly states the groups, baseline, support counts, and skipped-group rules.
- The strongest novelty in this project remains the explainable complaint pipeline; Phase 6 should therefore focus on proving that pipeline with repeatable evidence, not on inventing a second analytics product.

</sota_updates>

## Validation Architecture

Validation should cover three separate surfaces: taxonomy normalization, offline evaluation reporting, and reliability hardening.

- **Per task commit (quick):**
  - run the current task's `<automated>` verify command from the validation map
- **Per wave (full):**
  - `uv run pytest -q && uv run ruff check . && uv run mypy src`

Minimum guarantees:
1. The `eval` task runs a real holdout evaluation rather than a placeholder print.
2. Macro F1 plus class-level metrics are computed from normalized truth labels.
3. Fairness artifacts use a fixed product shortlist, named baseline, and explicit skipped-group warnings.
4. Empty, ambiguous, and very long complaints do not crash the pipeline.
5. Non-critical fallback or degrade paths remain visible without blocking successful runs.

<open_questions>
## Open Questions

1. **Exact fixed product shortlist**
   - Use the holdout distribution to choose a stable set with enough support; avoid groups that collapse almost entirely into noise after normalization.
2. **Artifact directory**
   - Decide whether Phase 6 writes reports under `data/eval/`, `artifacts/eval/`, or another deterministic location.
3. **Failure sample selection**
   - Decide whether failure examples are sampled by lowest confidence, highest severity mismatch, or first deterministic N after sorting.

</open_questions>

<sources>
## Sources

### Primary local sources
- `.planning/phases/06-evaluation-fairness-and-robustness/06-CONTEXT.md`
- `.planning/ROADMAP.md`
- `.planning/REQUIREMENTS.md`
- `.planning/STATE.md`
- `scripts/tasks.py`
- `scripts/build_dataset.py`
- `src/agents/classifier.py`
- `src/schemas/classification.py`
- `src/intake/pipeline.py`
- `src/intake/pii.py`
- `src/llm/client.py`
- `src/graph/routing.py`
- `src/ui/runtime.py`
- `tests/test_classifier_agent.py`
- `tests/test_intake_pipeline.py`
- `tests/test_llm_client.py`
- `tests/test_routing_interrupts.py`
- `tests/test_task_runner.py`
- `data/processed/metadata.json`
- `data/processed/holdout.parquet` (schema and distribution inspection)
- `tests/data_exploration.ipynb` (notebook prototype only; not production code)

### External sources
- No external sources were required for this phase research.

</sources>

<metadata>
## Metadata

**Research scope:** Phase 6 evaluation harness, fairness reporting, and reliability hardening strategy
**Confidence breakdown:**
- holdout data and taxonomy gap assessment: HIGH
- evaluation/reporting architecture: MEDIUM
- fairness metric framing for product groups: MEDIUM
- reliability warning surfacing plan: MEDIUM

**Research date:** 2026-04-08
**Valid until:** 2026-05-08
</metadata>

---

*Phase: 06-evaluation-fairness-and-robustness*
*Research completed: 2026-04-08*
*Ready for planning: yes*
