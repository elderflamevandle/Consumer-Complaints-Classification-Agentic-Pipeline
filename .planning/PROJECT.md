# FinComplaint AI

## What This Is

FinComplaint AI is a zero-cost, agentic AI workflow for consumer finance complaint triage and resolution drafting. It combines deterministic preprocessing with a LangGraph multi-agent pipeline to classify complaints, identify root cause, propose remediation, draft a response, and explain how each decision was made. The current target is a one-week MVP build (April 5, 2026 to April 11, 2026) that follows `plan2.md` as the primary execution baseline.

## Core Value

Turn an incoming complaint into a compliant, explainable recommended action in minutes at zero infrastructure cost.

## Requirements

### Validated

(None yet - ship to validate)

### Active

- [ ] End-to-end complaint pipeline: scrub -> classify -> root cause -> remediate -> write response -> audit -> explain
- [ ] Distinct MCP-backed remediation that grounds decisions in SLA/regulatory rules
- [ ] Human-in-the-loop controls for low-confidence or high-risk paths
- [ ] Streamlit demo UI with live pipeline visibility and audit trace
- [ ] Evaluation and fairness metrics to demonstrate responsible AI behavior

### Out of Scope

- Production hardening (multi-tenant auth, enterprise deployment) - not needed for one-week MVP
- Real legal/regulatory guarantees - demo uses mock SLA policy source
- Native mobile clients - web-first demo scope only
- Full OCR productization - include only mock receipt text extraction required for demo narrative

## Context

- Source materials analyzed:
  - `plan2.md` (primary execution guide)
  - `plan.md` (supporting detail and fallback architecture ideas)
- Scope direction:
  - Keep `plan2.md` advancements (MCP grounding, cyclic compliance auditor, Streamlit state-safe interrupts)
  - Use one-week execution pressure as the governing constraint
- Technical correction adopted from cross-plan analysis:
  - Use `mixtral-8x7b-32768` as fallback for `llama-3.3-70b-versatile`
  - Do not reference non-existent Groq fallback model names
- Delivery target:
  - Internal build complete by April 11, 2026
  - Submission package ready by April 15, 2026

## Constraints

- **Budget**: $0 infrastructure spend - all services/tools must remain free-tier or local
- **Timeline**: 7-day MVP build window - feature choices must prioritize demo reliability over breadth
- **LLM Provider**: Groq-first - keep model routing and fallbacks within Groq model availability
- **Demo Reliability**: Must support repeated golden-case demos - failure handling is mandatory, not optional
- **Explainability**: Every major decision path must be auditable in SQLite and visible in UI

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Use `plan2.md` as execution baseline | Contains stronger differentiation strategy (MCP + cyclic auditor) | - Pending |
| Keep one-week MVP cutline | Reduces risk of partial/incomplete demo | - Pending |
| Groq-only LLM provider for v1 | Lowest integration overhead and zero-cost objective alignment | - Pending |
| Model fallback chain: 70B -> Mixtral -> 8B | Aligns with known Groq model availability and reliability | - Pending |
| Use LangGraph with interrupts | Needed for HITL and auditor feedback loop routing | - Pending |
| Keep MCP as real boundary (not local mock function) | Required differentiator and architectural integrity for judging | - Pending |
| Streamlit as UI layer | Fastest path to demo-grade interface and controls | - Pending |
| Defer non-essential stretch goals to v2 | Protects delivery quality within one-week window | - Pending |

---
*Last updated: 2026-04-05 after initialization*
