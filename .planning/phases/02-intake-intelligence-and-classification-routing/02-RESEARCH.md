# Phase 2: Intake Intelligence and Classification Routing - Research

**Researched:** 2026-04-05
**Domain:** Intake preprocessing + strict classification + confidence/risk interrupt routing
**Confidence:** MEDIUM

<user_constraints>
## User Constraints (from 02-CONTEXT.md)

### Locked Decisions
- PII must be scrubbed before any LLM call.
- Redaction style uses typed placeholders (`[NAME]`, `[PHONE]`, `[EMAIL]`).
- Scrubbing policy is conservative-safe (balance privacy and semantic preservation).
- Persist both raw and scrubbed variants for traceability.
- Low-confidence scrub path:
  - Reviewer available -> route to human review before classification.
  - Reviewer unavailable -> continue with warning and high-risk flag.
- Routing trigger: `low confidence OR high compliance risk`.
- Confidence threshold baseline: `0.70`.
- Reviewer actions in scope: approve/edit/reject.
- Resume behavior: same thread continuation.
- AGT-02 classifier must output strict JSON fields:
  `product_type`, `issue_type`, `severity`, `compliance_risk`, `confidence`.
- Invalid schema handling: repair retries then model fallback.
- Schema-repair retries: `2`.
- Taxonomy strategy: constrained enums + `OTHER`.
- Missing/invalid confidence fallback: keyword-score heuristic.

### Carry-forward Constraints
- Groq-only provider in v1; shared reliability client in `src/llm/client.py`.
- Fallback chain fixed to `llama-3.3-70b-versatile -> mixtral-8x7b-32768 -> llama-3.1-8b-instant`.
- Keep deterministic behavior and test-first implementation style.

### Claude's Discretion
- Exact PII detector composition (regex/entity matching blend).
- Internal interrupt payload/state schema.
- DATA-04 receipt merge formatting and weighting details.

</user_constraints>

<research_summary>
## Summary

Phase 2 should prioritize deterministic contracts over model creativity. The safest implementation sequence is:
1. Build deterministic intake preprocessors (PII scrub + receipt merge) with explicit output payload.
2. Build strict classifier wrapper with schema repair and bounded retries.
3. Build routing/interrupt policy using classification + scrubber confidence + risk fields.

Core strategy: keep each policy boundary explicit and testable:
- `FLOW-01`: guaranteed pre-LLM scrubbing and failure policy
- `AGT-02`: guaranteed structured output contract
- `FLOW-02`: guaranteed interrupt behavior and same-thread resume

</research_summary>

<standard_stack>
## Standard Stack

### Core
| Library | Purpose | Why it fits this phase |
|---------|---------|------------------------|
| pydantic | strict schema validation | Deterministic JSON contract enforcement for AGT-02 |
| shared `GroqLLMClient` (`src/llm/client.py`) | resilient LLM calls | Reuses proven retry/fallback policies from Phase 1 |
| pytest | behavior contract tests | Fast policy-level verification |

### Supporting
| Library/Pattern | Purpose | Phase use |
|-----------------|---------|-----------|
| regex + typed redaction tokens | PII scrubbing | FLOW-01 pre-LLM safety gate |
| deterministic policy functions | routing logic | FLOW-02 reproducible branch behavior |
| typed dataclasses/pydantic models | intake/classifier/routing payloads | predictable inter-node handoff |

### Alternatives Considered
| Chosen | Alternative | Tradeoff |
|--------|-------------|----------|
| typed placeholder redaction | generic `[REDACTED]` token | more semantic context vs simpler implementation |
| constrained enums + `OTHER` | free-form labels | stronger downstream stability vs flexibility |
| threshold+policy routing | fully prompt-driven routing | reproducibility and testability vs less dynamic behavior |

</standard_stack>

<architecture_patterns>
## Architecture Patterns

### Pattern 1: Intake Safety Gate (Pre-LLM)
- `prepare_intake()` performs:
  1) raw complaint normalization
  2) PII scrubbing
  3) optional receipt text append
  4) safety metadata emission (`scrub_confidence`, warnings)
- LLM invocation receives scrubbed payload only.

### Pattern 2: Strict Classifier Envelope
- Classifier response pipeline:
  1) request strict JSON output
  2) parse/validate against pydantic schema
  3) repair prompt on parse failure (max 2)
  4) fallback model chain when repair budget exhausted
- Always emit deterministic fail-state object if final parse fails.

### Pattern 3: Policy-first Routing Node
- Routing input: classifier confidence, compliance risk, scrubber safety flags.
- Route decision must be pure-function style to maximize testability.
- Human interrupt payload includes original + scrubbed text references and recommendation reason.

### Pattern 4: Same-thread HITL Resume
- Resume handler consumes reviewer action (`approve`, `edit`, `reject`).
- Preserve thread state and append reviewer event to state history.
- Avoid resetting classifier call unless reviewer explicitly requests reclassify.

</architecture_patterns>

<dont_hand_roll>
## Don't Hand-Roll

| Problem | Avoid | Use Instead |
|---------|-------|-------------|
| ad hoc schema parsing | manual JSON `dict` checks everywhere | centralized pydantic parse/validation function |
| mixed routing conditions across nodes | inlined conditional branching | single routing policy function with tests |
| loss of scrub context | passing plain strings between nodes | structured intake payload with metadata |

</dont_hand_roll>

<common_pitfalls>
## Common Pitfalls

### Pitfall 1: Scrub-after-classify regression
- **Risk:** raw complaint text leaks to classifier before scrub step.
- **Prevent with:** explicit integration test asserting scrub call occurs before classifier invocation.

### Pitfall 2: Schema drift in classifier output
- **Risk:** small prompt changes produce invalid/extra fields.
- **Prevent with:** strict pydantic validation + repair retry + fallback.

### Pitfall 3: Over-triggered human interrupts
- **Risk:** threshold too strict floods reviewer queue.
- **Prevent with:** centralized threshold config and targeted test cases around boundary values.

### Pitfall 4: Ambiguous resume semantics
- **Risk:** review action breaks state continuity.
- **Prevent with:** route contract tests for each reviewer action and same-thread ID assertion.

</common_pitfalls>

<code_examples>
## Code Examples

### PII-first intake contract
```python
prepared = prepare_intake(raw_text=complaint, receipt_text=receipt)
assert prepared.scrubbed_text
assert prepared.raw_text
# classifier only receives scrubbed_text
```

### Strict classifier validation loop
```python
for attempt in range(2):
    payload = llm.complete(...)
    try:
        return ClassificationResult.model_validate_json(payload)
    except ValidationError:
        payload = llm.complete(prompt=repair_prompt(payload), ...)
```

### Deterministic route function
```python
def route(confidence: float, risk: str) -> str:
    if confidence < 0.70 or risk in {"high", "critical"}:
        return "human_review"
    return "continue"
```

</code_examples>

<sota_updates>
## State of the Art (2024-2025)

- LLM classification systems increasingly rely on schema-enforced outputs with repair loops.
- Safety-gated preprocessing before model calls is baseline for regulated-text workflows.
- HITL routing patterns trend toward explicit policy thresholds for auditability.

</sota_updates>

## Validation Architecture

Validation should sample every policy boundary with fast tests:

- **Per task commit (quick):**
  - `uv run pytest -q tests/test_intake_pipeline.py tests/test_classifier_agent.py`
- **Per wave (full):**
  - `uv run pytest -q && uv run ruff check . && uv run mypy src`

Minimum guarantees:
1. No unsanitized text reaches classifier path.
2. Classifier output contract is schema-valid or safely rerouted.
3. Routing policy behaves deterministically at threshold boundaries.

<open_questions>
## Open Questions

1. **Keyword-score heuristic source rules**
   - Need a fixed scoring rubric to keep fallback confidence deterministic.
2. **Receipt merge weighting**
   - Must decide whether receipt text is prefixed, suffixed, or section-tagged before classification.
3. **Reviewer availability signal**
   - Need canonical mechanism for "reviewer unavailable" in local MVP runtime.

</open_questions>

<sources>
## Sources

### Primary
- `.planning/phases/02-intake-intelligence-and-classification-routing/02-CONTEXT.md`
- `.planning/REQUIREMENTS.md`
- `.planning/ROADMAP.md`
- `.planning/STATE.md`

### Secondary
- `src/llm/client.py`
- `src/schemas/classification.py`

</sources>

<metadata>
## Metadata

**Research scope:** phase-specific implementation decisions and test strategy
**Confidence breakdown:**
- Intake safety policy: HIGH
- Classifier schema strategy: MEDIUM
- Routing semantics: HIGH

**Research date:** 2026-04-05
**Valid until:** 2026-05-05
</metadata>

---

*Phase: 02-intake-intelligence-and-classification-routing*
*Research completed: 2026-04-05*
*Ready for planning: yes*