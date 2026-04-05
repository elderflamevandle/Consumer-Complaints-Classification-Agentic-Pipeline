# Phase 3: Root Cause and MCP-Grounded Remediation - Context

**Gathered:** 2026-04-05
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase delivers diagnosis and policy-grounded remediation: root-cause analysis using top-5 similar complaints, mandatory MCP policy retrieval before remediation proposals, and consistent SQLite decision logging at node level.

</domain>

<decisions>
## Implementation Decisions

### Root-cause evidence contract (AGT-03)
- Root-cause output format is structured: one root-cause statement plus ranked evidence list.
- Evidence selection rule uses majority-theme first from top-5 retrieved complaints, while noting outliers.
- Evidence citations include: complaint `id`, `product`, `issue`, and `date`.
- If evidence is conflicting (no clear dominant cause), output includes explicit `AMBIGUOUS` flag.

### MCP remediation behavior (AGT-04)
- Remediator must call `get_sla_requirements(issue_type, state_code)` before proposing any action.
- If MCP policy call fails/unavailable: return `POLICY_UNAVAILABLE` and route remediation to human review path.
- MCP response must include minimum fields: `sla_window`, `required_actions`, `regulatory_basis`.
- Remediator output style: ordered action plan with policy citations tied to MCP fields.

### Audit logging contract (FLOW-05)
- SQLite logging granularity: one structured event per node outcome.
- Required log fields: `thread_id`, `node`, `timestamp`, `model`, `latency_ms`, `decision`.
- Logged complaint content is scrubbed text only (no raw complaint text in SQLite records).
- If SQLite write fails, pipeline continues with in-memory warning queue and emits audit warning event.

### Locked carry-forwards from prior phases
- Intake text is already scrubbed before model use (FLOW-01); phase 3 must preserve that boundary.
- Routing behavior from phase 2 remains deterministic and same-thread aware for human review transitions.
- LLM calls continue through shared Groq reliability wrapper and fixed fallback chain.

### Claude's Discretion
- Exact retrieval scoring and tie-break algorithm details inside top-5 selection.
- MCP transport/retry wrappers and local FastMCP service wiring details.
- SQLite table DDL naming/index choices as long as required fields and consistency contract are met.

</decisions>

<specifics>
## Specific Ideas

- Keep outputs explainable for judges/reviewers: every remediation step should reference policy source.
- Favor deterministic and auditable behavior over overly flexible free-form outputs.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/tools/vector_index.py`: manifest/hash utilities and local vector-index freshness contract.
- `scripts/seed_vectordb.py`: local vector/chroma seeding baseline and metadata field conventions.
- `src/agents/classifier.py`: strict schema-first agent pattern, retry/repair loop, deterministic fallback style.
- `src/graph/routing.py`, `src/graph/state.py`, `src/graph/interrupts.py`: established route/interrupt state contracts for same-thread decisions.

### Established Patterns
- Deterministic policy functions are validated by focused pytest regressions.
- Structured Pydantic schemas are used for machine-consumable contracts between stages.
- Shared LLM reliability behavior is centralized in `src/llm/client.py`.

### Integration Points
- Root-cause node should consume phase-2 classifier outputs and vector retrieval context.
- Remediator node should call MCP tool after diagnosis and before response planning.
- Logging hooks should attach to active graph nodes and preserve thread continuity from phase-2 state contracts.

</code_context>

<deferred>
## Deferred Ideas

- None - discussion stayed within phase scope.

</deferred>

---

*Phase: 03-root-cause-and-mcp-grounded-remediation*
*Context gathered: 2026-04-05*