# Feature Research

**Domain:** Agentic AI complaint resolution platform for consumer finance operations
**Researched:** 2026-04-05
**Confidence:** MEDIUM

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Structured complaint classification | Triage quality depends on consistent categorization | MEDIUM | Must include confidence score |
| Root-cause analysis with evidence | Teams need reasoned diagnosis, not only labels | MEDIUM | Use top-k retrieved similar complaints |
| Actionable remediation proposal | Operations users need next-step guidance | MEDIUM | Include cost/risk and approval flag |
| Human review interrupts | Compliance-sensitive flows cannot be fully autonomous | MEDIUM | Trigger on low confidence or high risk |
| Customer response draft | Reduces manual writing time | MEDIUM | Must avoid unauthorized promises |
| Audit log trail | Financial complaint handling needs traceability | LOW | Log model, timestamp, and decision payload |
| Demo-ready UI | Hackathon value depends on clear visibility | MEDIUM | Show pipeline state and key outputs |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valuable.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| MCP-grounded SLA policy retrieval | Demonstrates tool-augmented, policy-aware remediation | HIGH | Keep true MCP boundary, not in-process mock |
| Cyclic compliance auditor loop | Shows self-correction before final response | HIGH | Route fail -> response rewrite with critique |
| Zero-cost architecture instrumentation | Strong competition narrative | LOW | Explicitly track free-tier token usage |
| Explainability agent chain | Improves judge confidence and user trust | MEDIUM | Summarize why each agent decision happened |
| Golden scenario demo mode | Increases live demo reliability | LOW | One-click load for five curated cases |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Real-time streaming on all steps | Looks impressive in demos | Adds failure modes and UI complexity | Polling status updates with clear step transitions |
| Multi-provider LLM switching in v1 | Perceived resilience | Expands test matrix and integration overhead | Groq-only in v1 with robust in-provider fallback |
| Full legal automation promises | Sounds like strong value claim | High liability and factual risk | Decision-support framing with required human approval |
| Heavy OCR pipeline for all inputs | Feels multimodal | Slows dev and introduces extraction noise | Mock receipt text extraction for selected demo paths |
| Premature enterprise auth | Feels production-ready | Not needed for single-team hackathon demo | Keep local role assumptions for MVP |

## Feature Dependencies

```
PII scrubbing
    --requires--> complaint intake parsing
                    --feeds--> classification
                                  --feeds--> root-cause + remediation
                                                     --feeds--> response writer
                                                                      --reviewed-by--> compliance auditor
                                                                                              --if fail--> response writer

MCP SLA retrieval --required-by--> remediation quality

Audit logging --crosscuts--> all pipeline nodes
```

### Dependency Notes

- **Classification requires intake normalization:** Confidence thresholds are unstable without clean input.
- **Root-cause and remediation require retrieval + policy grounding:** Without both, remediation appears generic.
- **Auditor loop depends on message history:** Response writer must receive critique context to improve output.
- **HITL UI depends on stable thread state:** Streamlit reruns must preserve graph thread config.

## MVP Definition

### Launch With (v1)

Minimum viable product - what is needed to validate the concept.

- [ ] End-to-end multi-agent graph with MCP-backed remediation
- [ ] Cyclic auditor loop and human review interrupts
- [ ] Streamlit dashboard with audit trail and token visibility
- [ ] Golden demo mode with reliable repeatability

### Add After Validation (v1.x)

Features to add once core is working.

- [ ] LangSmith traces and richer observability layer
- [ ] Enhanced fairness drill-down and exportable reports
- [ ] API wrapper for non-UI integrations

### Future Consideration (v2+)

Features to defer until product-market fit is established.

- [ ] Production deployment topology (managed DB, hosted vector store)
- [ ] Advanced OCR and document ingestion pipeline
- [ ] Multi-region compliance policy backends

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| End-to-end graph execution | HIGH | MEDIUM | P1 |
| MCP-grounded remediation | HIGH | HIGH | P1 |
| Cyclic compliance auditor | HIGH | HIGH | P1 |
| Streamlit HITL controls | HIGH | MEDIUM | P1 |
| Fairness analytics tab | MEDIUM | MEDIUM | P2 |
| LangSmith integration | MEDIUM | LOW | P2 |
| Reasoning-model comparison mode | LOW | MEDIUM | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

## Competitor Feature Analysis

| Feature | Competitor A | Competitor B | Our Approach |
|---------|--------------|--------------|--------------|
| Complaint triage automation | Rule-heavy workflows | Single-LLM summarization | Multi-agent graph with explicit routing and confidence controls |
| Policy grounding | Static templates | Manual lookups | MCP tool call to policy rules per issue/state |
| Response QA loop | Manual QA only | One-pass generation | Automated auditor fail/pass cycle with rewrite feedback |
| Explainability | Minimal metadata logs | Opaque model output | Agent-by-agent rationale plus SQLite audit chain |

## Sources

- `f:/Agentic_Hackathon/plan2.md`
- `f:/Agentic_Hackathon/plan.md`
- `.planning/PROJECT.md`

---
*Feature research for: Agentic AI complaint resolution platform for consumer finance operations*
*Researched: 2026-04-05*
