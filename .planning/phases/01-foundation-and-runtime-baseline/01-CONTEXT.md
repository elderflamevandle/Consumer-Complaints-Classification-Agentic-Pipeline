# Phase 1: Foundation and Runtime Baseline - Context

**Gathered:** 2026-04-05
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase establishes deterministic project foundations: repository/runtime setup, Groq client reliability baseline, CFPB sampling workflow, and vector seeding baseline. It does not add later-phase capabilities (MCP remediation, UI experience, or auditor loop behavior).

</domain>

<decisions>
## Implementation Decisions

### Setup workflow and repository baseline
- Use `uv` with `pyproject.toml` for environment and dependency management.
- Create modular structure from day one (`src/`, `app/`, `scripts/`, `tests/`) instead of single-file bootstrap.
- Standardize commands via `Makefile` for `run`, `seed`, `eval`, and `test` workflows.
- Enforce initial quality baseline with `pytest`, `ruff`, and lightweight mypy checks.

### CFPB sampling strategy (10K)
- Use stratified sampling by product and issue (not pure random).
- Apply intake filters: non-empty narratives, minimum length threshold, and English-only.
- Partition data as `7k dev + 2k holdout + 1k demos`.
- Enforce reproducibility with fixed random seed and persisted parquet output.

### Chroma seeding contract (5K embeddings)
- Use higher-dimension embeddings with `bge-large-en-v1.5`.
- Persist local Chroma artifact directory with explicit version tag metadata.
- Keep auto rebuild behavior, but only when index is missing or stale.
- Define stale condition using dataset hash + embedding model id.
- If refresh fails, continue app with last valid index and show warning.

### Groq client reliability policy
- Retry policy: 3 retries with exponential backoff before fallback progression.
- Timeout policy: 45-second per-call timeout.
- Fallback triggers: HTTP 429, timeout errors, and transient 5xx responses.
- Budget behavior: warn near threshold and degrade non-critical 70B calls to lower-cost fallback model.

### Locked carry-forwards from project context
- Provider remains Groq-only for v1.
- Fallback chain remains fixed: `llama-3.3-70b-versatile -> mixtral-8x7b-32768 -> llama-3.1-8b-instant`.
- One-week MVP cutline is non-negotiable for planning tradeoffs.

### Claude's Discretion
- Exact folder/file naming inside each module directory as long as phase traceability remains clear.
- Exact lint/type strictness levels and threshold tuning for warning/degrade behavior.
- Operational log formatting for retry/fallback telemetry.

</decisions>

<specifics>
## Specific Ideas

- Strong preference for deterministic and repeatable local runs over minimal boilerplate.
- Preference for richer retrieval signal (`bge-large-en-v1.5`) even with added compute cost.
- Preference for resilient startup behavior (keep serving with last valid index when refresh fails).

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- No application source code exists yet (`src/` and `app/` are not present).
- Planning artifacts exist and should guide generated scaffolding:
  - `.planning/REQUIREMENTS.md`
  - `.planning/ROADMAP.md`
  - `.planning/research/SUMMARY.md`

### Established Patterns
- Architecture target is modular agent pipeline (per project/research docs), so phase scaffolding should align with `src/llm`, `src/agents`, `src/graph`, `src/tools`, `scripts`, and `tests` boundaries.
- Project-level decisions already lock Groq-first model routing and deterministic fallback chains.

### Integration Points
- Phase 1 outputs must support direct handoff to Phase 2 (`PII + classifier routing`) and Phase 3 (`RAG + MCP`) without structural refactor.
- Data artifacts created here (sample parquet, vector index metadata) become shared inputs for downstream agents and evaluation scripts.

</code_context>

<deferred>
## Deferred Ideas

- None - discussion stayed within phase scope.

</deferred>

---

*Phase: 01-foundation-and-runtime-baseline*
*Context gathered: 2026-04-05*
