# Phase 2: Intake Intelligence and Classification Routing - Context

**Gathered:** 2026-04-05
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase delivers intake preprocessing and first-step routing: PII scrubbing before any LLM call, optional mock receipt text append, strict classifier output, and confidence/risk-based interrupt routing to human review.

</domain>

<decisions>
## Implementation Decisions

### PII scrubbing policy
- Redact with typed placeholders (`[NAME]`, `[PHONE]`, `[EMAIL]`) instead of generic `[REDACTED]`.
- Use conservative-safe scrubbing: prioritize high-confidence PII removal while preserving complaint meaning.
- Persist both raw and scrubbed variants for traceability.
- If scrubber confidence is low and a reviewer is available: route to human review before classification.
- If scrubber confidence is low and reviewer is unavailable: continue with warning + high-risk flag on the same intake.

### Routing and interrupt behavior
- Trigger human-review interrupt when `low confidence OR high compliance risk`.
- Default confidence threshold for interrupt: `0.70`.
- Human reviewer actions in scope: `approve`, `edit`, `reject`.
- After human review, pipeline resumes on the same graph thread (no full restart).

### Classifier output contract
- AGT-02 output stays strict JSON contract (`product_type`, `issue_type`, `severity`, `compliance_risk`, `confidence`).
- On invalid schema output: auto-retry repair, then fallback through model chain before hard failure.
- Schema-repair retry budget: `2` attempts.
- Taxonomy strategy: constrained enums with explicit `OTHER` bucket for unknowns.
- If model confidence is missing/invalid: apply heuristic fallback via keyword-score estimate.

### Locked carry-forwards from Phase 1
- All LLM calls use shared Groq reliability wrapper in `src/llm/client.py`.
- Fallback chain remains fixed: `llama-3.3-70b-versatile -> mixtral-8x7b-32768 -> llama-3.1-8b-instant`.
- Deterministic, test-first implementation style remains required.

### Claude's Discretion
- Exact regex/entity-detection implementation for PII recognizers.
- Internal routing state shape and interrupt payload schema.
- Receipt-merge implementation details (`DATA-04`) including formatting and weighting, as long as merge happens before classification.

</decisions>

<specifics>
## Specific Ideas

- Keep routing behavior explicitly safety-biased for uncertain or risky complaints.
- Maintain deterministic defaults where possible, even when heuristic fallback is used.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/schemas/classification.py`: existing strict classification schema baseline to extend for Phase 2 contract enforcement.
- `src/llm/client.py`: centralized retry/timeout/fallback policy wrapper for classifier calls.
- `src/config.py`: shared runtime settings source for thresholds/feature flags.

### Established Patterns
- Deterministic policies are encoded in central modules and covered by focused pytest suites.
- Tooling baseline (`pytest`, `ruff`, `mypy`) is already enforced through Makefile and CI-friendly commands.
- Typed/Pydantic contracts are preferred for machine-consumable outputs.

### Integration Points
- Intake preprocessing and routing logic should connect under `src/agents` and/or `src/graph` boundaries.
- Interrupt outcomes must preserve thread continuity for downstream phases.
- New behaviors should be regression-tested under `tests/` with policy-level assertions.

</code_context>

<deferred>
## Deferred Ideas

- None - discussion stayed within phase scope.

</deferred>

---

*Phase: 02-intake-intelligence-and-classification-routing*
*Context gathered: 2026-04-05*