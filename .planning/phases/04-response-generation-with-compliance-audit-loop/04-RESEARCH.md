# Phase 4: Response Generation with Compliance Audit Loop - Research

**Researched:** 2026-04-05
**Domain:** Customer response drafting + compliance audit rewrite loop + explainability output
**Confidence:** MEDIUM

<user_constraints>
## User Constraints (from 04-CONTEXT.md)

### Locked Decisions
- Auditor verdict format is `PASS/FAIL` with explicit reason codes.
- Rewrite loop cap is `2` retries, then escalation to human review.
- Writer carry-forward context includes latest draft plus unresolved critique items.
- Critique priority is unresolved must-fix items first, then newest cycle critique.
- Required auditor checks are compliance safety, policy grounding, and customer-safe tone together.
- Per-cycle trace must persist cycle number, verdict, fail codes, and critique summary.
- Writer tone is calm professional.
- Writer draft uses fixed 4-block structure:
  1. acknowledgment
  2. findings
  3. action steps
  4. timeline/next steps
- Customer response includes explicit policy citation labels.
- Commitment guardrails are strict: no liability admissions and no guaranteed outcomes.
- Explainer audience is judge/reviewer first.
- Explainer output is deterministic stage-chain bullets with selective citations.
- Explainer target length is `5-7` bullets.
- Inputs remain scrubbed-safe artifacts only.
- Phase 3 audit logging remains active and must extend to Phase 4 nodes.

### Carry-forward Constraints
- FLOW-01 scrub boundary remains enforced for all new agents.
- AGT-04 remediation already provides ordered policy-grounded actions and citations.
- FLOW-02 deterministic thread continuity and review transitions remain in force.
- All LLM calls continue through the shared Groq fallback wrapper and model registry.

### Claude's Discretion
- Canonical reason-code taxonomy and ordering.
- Exact prompt structure for writer, auditor, and explainer.
- Exact state field names as long as bounded critique-memory behavior is preserved.

</user_constraints>

<research_summary>
## Summary

Phase 4 should be implemented as a bounded state-backed rewrite loop, not a prompt-only self-correction pattern:
1. Establish a schema-validated writer contract for customer-facing drafts (AGT-05).
2. Add a reason-coded auditor plus deterministic rewrite routing with retry cap (AGT-06).
3. Persist bounded critique history and expose a final stage-chain explainer over structured artifacts (AGT-07 + FLOW-03).

Recommended strategy:
- Keep writer output machine-readable first, then render the customer-facing text from the structured draft.
- Keep auditor critique machine-readable with stable reason codes so routing and rewrite behavior are deterministic.
- Persist only the latest draft, unresolved issues, and compact cycle trace. Do not store unbounded conversational transcripts.
- Build the explainer from classification, diagnosis, remediation, response, and audit artifacts already produced by earlier phases.

</research_summary>

<standard_stack>
## Standard Stack

### Core
| Library/Module | Purpose | Why it fits this phase |
|----------------|---------|------------------------|
| `pydantic` schemas | Draft, critique, verdict, and explanation contracts | Matches schema-first patterns already used in classifier, root-cause, and remediator |
| `src/llm/client.py` + `src/llm/models.py` | Reliable writer/auditor/explainer completions | Reuses existing retry and fallback guarantees |
| `src/graph/state.py` | Bounded rewrite memory and cycle trace | Already owns thread-scoped routing state |
| `src/tools/audit_logger.py` | Node-level event logging for writer/auditor/explainer | Extends Phase 3 audit contract without new persistence primitives |

### Supporting
| Library/Pattern | Purpose | Phase use |
|-----------------|---------|-----------|
| deterministic render helper | stable 4-block customer response text | keeps output easy to test and demo |
| reason-code enum | machine-readable audit failures | powers rewrite routing and critique prioritization |
| bounded cycle history | latest draft + unresolved issues + cycle summaries | satisfies FLOW-03 without transcript sprawl |

### Alternatives Considered
| Chosen | Alternative | Tradeoff |
|--------|-------------|----------|
| schema-first writer output | free-form markdown from the writer | stronger regression tests and safer downstream audit |
| separate auditor pass with coded verdicts | single prompt that writes and self-checks | clearer failure modes and deterministic routing |
| bounded state memory | full transcript storage | less noise, lower risk, easier explainability |

</standard_stack>

<architecture_patterns>
## Architecture Patterns

### Pattern 1: Structured Response Envelope (AGT-05)
- Writer should return a schema with:
  - `resolution_statement`
  - `acknowledgment`
  - `findings`
  - `action_steps[]`
  - `timeline_next_steps`
  - `policy_citation_labels[]`
- A small render helper can assemble the fixed 4-block customer message from the schema while keeping tests focused on structure and guardrails.
- Guardrails should be enforced twice: prompt instruction plus post-parse text checks for banned commitment patterns.

### Pattern 2: Reason-Coded Auditor Gate (AGT-06)
- Auditor output should include:
  - `verdict` (`PASS` or `FAIL`)
  - `reason_codes[]`
  - `critique_summary`
  - `must_fix_items[]`
  - `rewrite_recommended`
- Fail codes should be stable strings such as:
  - `MISSING_POLICY_CITATION`
  - `UNSAFE_TONE`
  - `OVERCOMMITMENT`
  - `STRUCTURE_MISSING`
  - `UNCLEAR_RESOLUTION`
- PASS/FAIL should be based on structured checks, not open-ended prose.

### Pattern 3: Bounded Rewrite Memory (FLOW-03)
- Extend graph state with compact Phase 4 fields:
  - latest draft
  - current rewrite count
  - unresolved critique items
  - cycle trace entries
  - final auditor verdict
- Preserve only scrubbed-safe summaries and structured artifacts.
- Rewrite input assembly should prioritize unresolved issues first, then newest critique, exactly as locked in context.

### Pattern 4: Final Stage-Chain Explainer (AGT-07)
- Explainer should consume structured outputs from:
  - classification
  - root-cause diagnosis
  - remediation
  - final writer draft
  - final auditor verdict
- Output should be deterministic 5-7 bullets in stage order.
- Selective citations should point to the supporting stage artifact, not dump every retrieved item or audit event.

</architecture_patterns>

<dont_hand_roll>
## Don't Hand-Roll

| Problem | Avoid | Use Instead |
|---------|-------|-------------|
| writer output shape drift | raw string concatenation only | typed response schema plus renderer |
| unstructured critique | prose-only auditor feedback | verdict model with reason-code enum and must-fix items |
| transcript sprawl | appending every draft and full audit prompt to state | bounded latest-draft and unresolved-issues fields |
| explanation drift | explainer reads raw complaint and improvises rationale | explainer builds from prior stage outputs and final verdict |

</dont_hand_roll>

<common_pitfalls>
## Common Pitfalls

### Pitfall 1: Writer promises outcomes it cannot guarantee
- **Risk:** customer-facing response violates compliance posture.
- **Prevent with:** banned-phrase checks for liability admissions and guarantees, plus dedicated regression tests.

### Pitfall 2: Auditor critique is not machine-readable
- **Risk:** rewrite loop becomes non-deterministic and hard to route.
- **Prevent with:** fixed verdict schema, stable reason codes, and explicit rewrite counter handling.

### Pitfall 3: FLOW-03 stores raw or unbounded history
- **Risk:** larger state surface, scrub-boundary regressions, noisy rewrites.
- **Prevent with:** persist only structured latest draft, unresolved items, and compact cycle summaries.

### Pitfall 4: Explainer restates prompt language instead of actual decisions
- **Risk:** rationale chain no longer matches executed pipeline artifacts.
- **Prevent with:** explainer input should be prior stage outputs and final audit decision only.

</common_pitfalls>

<code_examples>
## Code Examples

### Writer draft contract
```python
draft = writer.compose_response(
    complaint_text=intake.scrubbed_text,
    classification=classification,
    diagnosis=diagnosis,
    remediation=remediation,
    unresolved_issues=state.unresolved_issues,
)
assert draft.resolution_statement
assert draft.policy_citation_labels
```

### Auditor verdict contract
```python
verdict = auditor.review_response(draft=draft, remediation=remediation)
if verdict.verdict == "FAIL" and state.rewrite_count >= 2:
    route = "human_review"
```

### Bounded critique memory
```python
state = state.model_copy(
    update={
        "latest_response_draft": draft,
        "rewrite_count": state.rewrite_count + 1,
        "unresolved_issues": verdict.must_fix_items,
    }
)
```

### Stage-chain explanation
```python
explanation = explainer.summarize_chain(
    classification=classification,
    diagnosis=diagnosis,
    remediation=remediation,
    final_response=draft,
    audit_verdict=verdict,
)
assert 5 <= len(explanation.bullets) <= 7
```

</code_examples>

<sota_updates>
## State of the Art (2024-2025)

- Generator-plus-auditor loops are increasingly used for regulated-domain response drafting because critique becomes inspectable and testable.
- Safety-critical rewrite systems trend toward bounded memory rather than transcript replay to reduce prompt noise and preserve determinism.
- Explainability is strongest when produced from structured stage outputs instead of a separate model re-deriving the pipeline story from raw input.

</sota_updates>

## Validation Architecture

Validation should target each contract boundary in AGT-05, AGT-06, AGT-07, and FLOW-03.

- **Per task commit (quick):**
  - `uv run pytest -q tests/test_response_writer.py tests/test_auditor_loop.py tests/test_explainer_agent.py tests/test_phase4_state.py`
- **Per wave (full):**
  - `uv run pytest -q && uv run ruff check . && uv run mypy src`

Minimum guarantees:
1. Writer always returns a schema-valid customer draft with a clear resolution statement, fixed 4-block structure, and safe-tone guardrails.
2. Auditor always returns `PASS/FAIL` plus reason codes, and failed reviews route into a capped rewrite loop or human review escalation.
3. Graph state carries bounded critique memory across rewrites without storing raw unbounded transcripts.
4. Explainer returns deterministic stage-chain bullets grounded in actual stage outputs and final audit verdict.

<open_questions>
## Open Questions

1. **Reason-code taxonomy depth**
   - Decide whether to keep a short core set or include finer-grained audit distinctions during execution.
2. **Response rendering format**
   - Decide whether rendered customer output should be plain text or markdown while keeping the same 4-block schema.
3. **Explanation evidence source**
   - Decide whether explainer should cite only stage artifacts or also include selected node audit decisions.

</open_questions>

<sources>
## Sources

### Primary
- `.planning/phases/04-response-generation-with-compliance-audit-loop/04-CONTEXT.md`
- `.planning/ROADMAP.md`
- `.planning/REQUIREMENTS.md`
- `.planning/STATE.md`

### Secondary
- `src/graph/state.py`
- `src/graph/routing.py`
- `src/graph/interrupts.py`
- `src/agents/root_cause.py`
- `src/agents/remediator.py`
- `src/tools/audit_logger.py`
- `src/llm/models.py`

</sources>

<metadata>
## Metadata

**Research scope:** Phase 4 implementation strategy and verification contract
**Confidence breakdown:**
- AGT-05 writer contract: HIGH
- AGT-06 auditor loop behavior: MEDIUM
- FLOW-03 bounded rewrite memory: MEDIUM
- AGT-07 explanation chain: MEDIUM

**Research date:** 2026-04-05
**Valid until:** 2026-05-05
</metadata>

---

*Phase: 04-response-generation-with-compliance-audit-loop*
*Research completed: 2026-04-05*
*Ready for planning: yes*
