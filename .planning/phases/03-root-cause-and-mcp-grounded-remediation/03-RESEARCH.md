# Phase 3: Root Cause and MCP-Grounded Remediation - Research

**Researched:** 2026-04-05
**Domain:** Retrieval-grounded diagnosis + MCP policy retrieval + node-level audit persistence
**Confidence:** MEDIUM

<user_constraints>
## User Constraints (from 03-CONTEXT.md)

### Locked Decisions
- Root-cause output is structured: one diagnosis statement plus ranked evidence list.
- Evidence uses majority-theme-first from top-5 retrieved complaints.
- Evidence citations must include `id`, `product`, `issue`, and `date`.
- Conflicting evidence must set explicit `AMBIGUOUS` flag.
- Remediator must call `get_sla_requirements(issue_type, state_code)` before proposing actions.
- If MCP call fails/unavailable, emit `POLICY_UNAVAILABLE` and route to human review.
- MCP payload must include `sla_window`, `required_actions`, and `regulatory_basis`.
- Remediation output must be an ordered action plan with policy citations.
- Log one structured SQLite event per node outcome.
- Required event fields: `thread_id`, `node`, `timestamp`, `model`, `latency_ms`, `decision`.
- SQLite logs must store scrubbed text only; never raw complaint text.
- SQLite write failure must not crash pipeline; queue warning and continue.

### Carry-forward Constraints
- FLOW-01 scrub boundary remains enforced: downstream phase-3 nodes consume scrubbed/classifier payloads.
- FLOW-02 routing semantics and same-thread review continuation remain deterministic.
- All LLM calls continue through shared Groq reliability wrapper and fallback chain.

### Claude's Discretion
- Retrieval scoring and deterministic tie-break details inside top-5 selection.
- MCP transport mode (stdio/SSE), retry limits, and timeout defaults.
- SQLite schema/index details as long as required logging contract is preserved.

</user_constraints>

<research_summary>
## Summary

Phase 3 should be implemented in three sequential contracts:
1. Retrieval + root-cause evidence schema (AGT-03).
2. FastMCP policy boundary + remediation grounding (AGT-04).
3. Node-level SQLite audit event writing with fail-open behavior (FLOW-05).

Recommended strategy is policy-first orchestration, not free-form generation:
- Root-cause stage must expose why a diagnosis was chosen (ranked evidence + citations).
- Remediator must be blocked on MCP policy retrieval to keep recommendations traceable.
- Audit logging should be centralized in one lightweight logger utility and called by each active node.

</research_summary>

<standard_stack>
## Standard Stack

### Core
| Library/Module | Purpose | Why it fits this phase |
|----------------|---------|------------------------|
| `src/tools/vector_index.py` + Chroma/json-fallback artifacts | Retrieval freshness + metadata conventions | Reuses seeded index and manifest guarantees from Phase 1 |
| `pydantic` schemas | Structured diagnosis/remediation contracts | Prevents schema drift between root-cause/remediator/logging stages |
| `sqlite3` (stdlib) | Node-level event persistence | Zero-cost local audit trail aligned to FLOW-05 |
| shared `GroqLLMClient` (`src/llm/client.py`) | Reliable LLM calls and fallback behavior | Keeps Phase 3 model behavior consistent with prior phases |

### Supporting
| Library/Pattern | Purpose | Phase use |
|-----------------|---------|-----------|
| FastMCP server (local process) | External SLA/policy lookup boundary | Enforces AGT-04 tool-grounding requirement |
| deterministic retrieval utility | top-5 evidence fetch with stable ordering | Ensures reproducible root-cause context |
| warning queue fallback | fail-open logging resilience | Prevents SQLite outages from blocking graph progress |

### Alternatives Considered
| Chosen | Alternative | Tradeoff |
|--------|-------------|----------|
| explicit MCP client call before remediation | embedding policy text directly in prompts | stronger architectural credibility and testability |
| centralized audit logger utility | ad hoc per-node `sqlite3` writes | less duplication and consistent event schema |
| deterministic top-5 retrieval wrapper | direct inline vector calls in agent | better reproducibility and easier regression testing |

</standard_stack>

<architecture_patterns>
## Architecture Patterns

### Pattern 1: Deterministic Retrieval Envelope (AGT-03)
- Build one retriever function that returns exactly top-5 similar complaints with stable ordering.
- Include citation metadata in retriever output so root-cause agent does not reconstruct citations ad hoc.
- Tie-break recommendation: similarity score desc, then complaint `id` asc.

### Pattern 2: Evidence-First Root Cause Contract (AGT-03)
- Root-cause agent output schema should include:
  - `root_cause`
  - `evidence[]` (ranked, with citation fields)
  - `ambiguous` boolean/flag
- `AMBIGUOUS` should be triggered by majority-theme conflict thresholds defined in code, not prompt prose only.

### Pattern 3: Mandatory MCP Policy Gate (AGT-04)
- Remediator flow:
  1) receive diagnosis + classification
  2) call MCP tool `get_sla_requirements(issue_type, state_code)`
  3) validate required MCP fields
  4) generate ordered remediation plan with policy citations
- On MCP failure/invalid fields, emit `POLICY_UNAVAILABLE` and route for review instead of guessing policy.

### Pattern 4: Structured Audit Hooking (FLOW-05)
- Introduce `audit_logger.log_node_outcome(...)` as single write path.
- Call logger from active node boundaries (classifier route, root-cause output, remediator output, review transitions).
- Store scrubbed text snippets only, never raw intake text.
- If SQLite write fails: append warning object to in-memory queue and emit warning event.

</architecture_patterns>

<dont_hand_roll>
## Don't Hand-Roll

| Problem | Avoid | Use Instead |
|---------|-------|-------------|
| free-form evidence blobs | untyped dicts from root-cause output | pydantic evidence schema with required citation fields |
| hidden MCP shortcuts | local helper masquerading as policy tool | explicit MCP client call path with tool discovery/validation |
| duplicated SQL writes | per-module SQL strings and schema drift | centralized logger module with one insert contract |

</dont_hand_roll>

<common_pitfalls>
## Common Pitfalls

### Pitfall 1: Retrieval context includes unsanitized text
- **Risk:** raw complaint PII leaks into diagnosis context.
- **Prevent with:** pass scrubbed/classifier payload fields only into retrieval/query generation.

### Pitfall 2: MCP call is optional in practice
- **Risk:** remediator emits actions without SLA basis.
- **Prevent with:** hard precondition check and explicit `POLICY_UNAVAILABLE` branch.

### Pitfall 3: Inconsistent audit event schema
- **Risk:** downstream audit UI/query code breaks on shape drift.
- **Prevent with:** single schema model + integration tests for required fields.

### Pitfall 4: SQLite failures halt pipeline
- **Risk:** transient file lock or path issue blocks all processing.
- **Prevent with:** fail-open warning queue and warning event emission.

</common_pitfalls>

<code_examples>
## Code Examples

### Deterministic top-5 retrieval
```python
results = retrieve_similar_cases(query_text=scrubbed_text, limit=5)
assert len(results) <= 5
assert all({"id", "product", "issue", "date"} <= set(r.citation.keys()) for r in results)
```

### Mandatory MCP gate
```python
policy = mcp_client.get_sla_requirements(issue_type=issue, state_code=state)
if policy is None or not policy.has_required_fields():
    return RemediationResult(status="POLICY_UNAVAILABLE", route="human_review")
```

### Node-level audit logging with fail-open behavior
```python
logger.log_node_outcome(
    thread_id=thread_id,
    node="remediator",
    model=response.model,
    latency_ms=latency_ms,
    decision="policy_grounded_action_plan",
    scrubbed_excerpt=scrubbed_excerpt,
)
```

</code_examples>

<sota_updates>
## State of the Art (2024-2025)

- Regulated-domain agent pipelines increasingly require explicit tool-grounding boundaries rather than prompt-only rules.
- Retrieval-backed diagnosis quality improves when evidence citations are first-class schema fields, not optional narrative text.
- Auditability expectations emphasize per-node structured events and deterministic failure handling.

</sota_updates>

## Validation Architecture

Validation should target each hard contract in AGT-03, AGT-04, and FLOW-05.

- **Per task commit (quick):**
  - `uv run pytest -q tests/test_root_cause_agent.py tests/test_remediator_mcp.py tests/test_audit_logger.py`
- **Per wave (full):**
  - `uv run pytest -q && uv run ruff check . && uv run mypy src`

Minimum guarantees:
1. Root-cause stage always returns structured diagnosis with ranked evidence citations or explicit `AMBIGUOUS`.
2. Remediator never returns action plan without a successful MCP policy retrieval or `POLICY_UNAVAILABLE` fallback.
3. Every active node outcome attempts structured SQLite logging with fail-open warning behavior on write failure.

<open_questions>
## Open Questions

1. **MCP transport selection**
   - Decide whether stdio or SSE transport is preferred for local demo stability.
2. **Ambiguity threshold tuning**
   - Final rule for majority-theme conflict needs explicit numeric threshold in code.
3. **Audit table retention policy**
   - Decide whether to cap local audit DB rows during repeated demo runs.

</open_questions>

<sources>
## Sources

### Primary
- `.planning/phases/03-root-cause-and-mcp-grounded-remediation/03-CONTEXT.md`
- `.planning/ROADMAP.md`
- `.planning/REQUIREMENTS.md`
- `.planning/STATE.md`

### Secondary
- `src/tools/vector_index.py`
- `scripts/seed_vectordb.py`
- `src/llm/client.py`
- `src/graph/state.py`
- `src/graph/routing.py`
- `src/graph/interrupts.py`

</sources>

<metadata>
## Metadata

**Research scope:** Phase-3 implementation strategy and verification contract
**Confidence breakdown:**
- AGT-03 retrieval/evidence contract: HIGH
- AGT-04 MCP policy gate behavior: MEDIUM
- FLOW-05 audit persistence design: MEDIUM

**Research date:** 2026-04-05
**Valid until:** 2026-05-05
</metadata>

---

*Phase: 03-root-cause-and-mcp-grounded-remediation*
*Research completed: 2026-04-05*
*Ready for planning: yes*
