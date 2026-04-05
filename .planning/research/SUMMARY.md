# Project Research Summary

**Project:** FinComplaint AI
**Domain:** Agentic AI complaint resolution for consumer finance operations
**Researched:** 2026-04-05
**Confidence:** MEDIUM

## Executive Summary

FinComplaint AI should be built as a modular, stateful multi-agent workflow with explicit safety and compliance controls. The most defensible implementation path is the `plan2.md` architecture: MCP-grounded remediation, cyclic compliance auditing, and a clear human-in-the-loop path in Streamlit. This structure gives strong demo differentiation while preserving explainability.

The one-week delivery constraint requires strict scope discipline. The project should prioritize deterministic data contracts, robust fallback behavior, and repeatable golden demos over broad feature expansion. `plan.md` contributes useful supporting practices (token tracking, evaluation framing), while `plan2.md` provides the stronger product narrative and advanced architecture patterns.

Primary risk is integration complexity (MCP boundary, auditor loop routing, and Streamlit session continuity). These risks are manageable if implemented in phase order and validated with focused reliability checks before demo packaging.

## Key Findings

### Recommended Stack

Python + LangGraph + Groq + Streamlit is the most practical zero-cost combination for this project type. Pydantic schemas are non-negotiable to stabilize outputs across multiple agent hops. ChromaDB + MiniLM embeddings provides low-overhead retrieval quality for root-cause grounding.

**Core technologies:**
- Python: runtime and ecosystem depth for agentic orchestration
- LangGraph: interrupt-aware state machine for HITL and cyclic QA
- Groq models: speed and free-tier compatibility for multi-call pipelines
- Pydantic: typed contracts for parse safety and routing confidence
- Streamlit: rapid UI iteration for demo deadlines

### Expected Features

**Must have (table stakes):**
- Multi-stage complaint triage with confidence-aware routing
- Human review and auditable decision history
- Response drafting and explainability chain

**Should have (competitive):**
- MCP policy grounding in remediation
- Cyclic compliance auditor with rewrite loop
- Golden demo mode and token-usage transparency

**Defer (v2+):**
- Production deployment architecture
- Full OCR and document ingestion platform
- Multi-provider LLM abstraction

### Architecture Approach

Use a layered architecture where Streamlit controls input/resume actions, LangGraph owns process state and routing, and agent/tool modules remain isolated and testable. Keep policy grounding (MCP), retrieval, and auditing as explicit boundaries so each can be demonstrated and validated independently.

**Major components:**
1. Intake and preprocessing pipeline - complaint normalization and PII controls
2. Agentic reasoning graph - classification through explainability with loop/interrupt gates
3. Tooling and persistence layer - MCP policy calls, vector retrieval, and SQLite audit storage

### Critical Pitfalls

1. **Invalid fallback models** - validate model IDs and test fallback branches early.
2. **Mocked MCP boundary** - keep true external tool invocation for credibility.
3. **Broken auditor loop** - cap retry count and preserve critique history.
4. **Streamlit state resets** - persist thread configuration in session state.
5. **Demo-only validation** - run edge-case and repeatability checks before freeze.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Foundation and Runtime Baseline
**Rationale:** Reliability starts with correct model routing, data prep, and project scaffolding.
**Delivers:** Working Groq client, sampled dataset, seeded vector baseline.
**Addresses:** Core stack risk and fallback correctness.
**Avoids:** Runtime failures from invalid model/fallback setup.

### Phase 2: Intake Intelligence
**Rationale:** Early complaint understanding unlocks the rest of the pipeline.
**Delivers:** PII scrub + OCR intake + classifier with confidence routing.
**Uses:** Schema-first validation patterns.
**Implements:** First interrupt branch for low confidence.

### Phase 3: Diagnosis and Policy-Grounded Remediation
**Rationale:** Root-cause + remediation is the product intelligence core.
**Delivers:** RAG-backed diagnosis and real MCP policy lookup.
**Uses:** Retrieval and tool-calling boundaries.
**Implements:** Compliance-aware action proposals.

### Phase 4: Response Quality Control Loop
**Rationale:** Response quality determines trust and demo impact.
**Delivers:** Writer + auditor cycle + explainer chain.
**Uses:** Cyclic graph routing.
**Implements:** Self-correction behavior.

### Phase 5: Interactive Demo UX
**Rationale:** Judges evaluate what they can see and control.
**Delivers:** Streamlit dashboard with HITL, telemetry, and audit views.
**Uses:** Session-state thread management.
**Implements:** Resume-safe interrupts.

### Phase 6: Evaluation and Robustness
**Rationale:** Metrics and resilience convert prototype into credible system.
**Delivers:** Accuracy, fairness, edge-case handling, and reliability tests.

### Phase 7: Demo Hardening and Submission Packaging
**Rationale:** Final quality pass ensures stable presentation execution.
**Delivers:** Golden demo validation, performance tuning, and submission artifacts.

### Phase Ordering Rationale

- Ordering follows hard dependencies: intake before diagnosis, diagnosis before response, response before UX polish.
- High-risk integrations (MCP and cyclic loop) are front-loaded before UI-heavy work.
- Reliability and evaluation happen before final demo freeze to reduce presentation risk.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3:** MCP transport details and robust tool-failure handling.
- **Phase 6:** Fairness metric interpretation and threshold policy framing.

Phases with standard patterns (skip research-phase):
- **Phase 1:** Project scaffolding, client wrappers, and dataset preparation.
- **Phase 5:** Streamlit layout and interaction wiring patterns.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM | Strong alignment with existing plans; no external doc verification in this pass |
| Features | MEDIUM | Clear pattern synthesis from both plan files |
| Architecture | MEDIUM | Good internal consistency; integration details still execution-sensitive |
| Pitfalls | MEDIUM | Derived from known failure modes in this architecture style |

**Overall confidence:** MEDIUM

### Gaps to Address

- Confirm exact MCP Python SDK ergonomics during implementation spike.
- Validate fairness grouping fields available in selected CFPB subset.
- Establish explicit max-iteration policy for auditor rewrite loop.

## Sources

### Primary (HIGH confidence)
- `f:/Agentic_Hackathon/plan2.md` - execution priorities and advanced architecture
- `f:/Agentic_Hackathon/plan.md` - support details for fallback, evaluation, and observability framing

### Secondary (MEDIUM confidence)
- `.planning/PROJECT.md` constraints and delivery framing

### Tertiary (LOW confidence)
- No external web verification used in this initialization pass

---
*Research completed: 2026-04-05*
*Ready for roadmap: yes*
