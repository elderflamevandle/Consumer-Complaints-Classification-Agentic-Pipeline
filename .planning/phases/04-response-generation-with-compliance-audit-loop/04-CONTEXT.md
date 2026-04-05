# Phase 4: Response Generation with Compliance Audit Loop - Context

**Gathered:** 2026-04-05
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase delivers customer-facing response drafting, compliance auditing with rewrite loop behavior, and final explainability output that summarizes the decision chain.

</domain>

<decisions>
## Implementation Decisions

### Auditor loop contract (AGT-06 + FLOW-03)
- Auditor verdict format is `PASS/FAIL` with explicit reason codes.
- Rewrite loop cap is `2` retries, then escalation to human review.
- Writer carry-forward context includes latest draft plus unresolved critique items (not full unbounded history).
- Critique priority rule is unresolved must-fix items first, then newest cycle-specific critique.
- Required auditor checks: compliance safety, policy grounding, and customer-safe tone together.
- Per-cycle persisted trace includes cycle number, verdict, fail codes, and critique summary.

### Response writer contract (AGT-05)
- Default tone is calm professional.
- Draft shape uses fixed 4-block structure:
  1) acknowledgment
  2) findings
  3) action steps
  4) timeline/next steps.
- Customer response includes explicit policy citation labels (not hidden).
- Commitment guardrails are strict: no liability admissions and no guaranteed outcomes.

### Explainer contract (AGT-07)
- Primary audience is judge/reviewer (audit and demo clarity first).
- Output format is stage-chain bullets in deterministic order.
- Evidence density is selective citations per stage (not no-citation, not full detail dump).
- Length target is 5-7 bullets.

### Locked carry-forwards from prior phases
- Inputs to writer/auditor/explainer remain scrubbed-safe artifacts (FLOW-01 boundary preserved).
- Remediation output already includes policy-grounded actions and citations from MCP contract (AGT-04).
- Routing and thread continuity behavior remain deterministic from Phase 2.
- Node-level logging contract from Phase 3 remains active and should extend to new Phase 4 nodes.

### Claude's Discretion
- Exact fail-code taxonomy names and canonical ordering.
- Prompt wording and scoring heuristics for writer/auditor/explainer as long as locked contracts are preserved.
- Exact state model field names for critique history, provided FLOW-03 memory behavior is satisfied.

</decisions>

<specifics>
## Specific Ideas

- Keep loop outputs easy to judge live: deterministic verdicts, reason codes, and concise explainability.
- Prefer consistent, auditable response structure over creative variation.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/agents/remediator.py`: policy-grounded action plan output + `POLICY_UNAVAILABLE` safety route.
- `src/agents/root_cause.py`: structured diagnosis/evidence schema and fallback ambiguity handling.
- `src/tools/audit_logger.py`: centralized SQLite event writer with fail-open warning queue.
- `src/graph/routing.py`, `src/graph/interrupts.py`, `src/graph/state.py`: deterministic thread and review-transition patterns.
- `src/llm/models.py`: pre-registered agent names already include `writer`, `auditor`, and `explainer`.

### Established Patterns
- Schema-first pydantic contracts for inter-node outputs.
- Deterministic policy decisions covered by focused pytest suites.
- Shared Groq reliability wrapper and fallback chain via `src/llm/client.py`.

### Integration Points
- Writer should consume remediation result and produce draft payload for auditor.
- Auditor should emit coded fail/pass result and critique payload consumed by writer loop.
- FLOW-03 state extension should carry unresolved critique items and cycle metadata across rewrites.
- Explainer should consume final writer/auditor artifacts plus logged node decisions for final rationale chain.

</code_context>

<deferred>
## Deferred Ideas

- None - discussion stayed within phase scope.

</deferred>

---

*Phase: 04-response-generation-with-compliance-audit-loop*
*Context gathered: 2026-04-05*
