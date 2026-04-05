# Roadmap: FinComplaint AI

## Overview

This roadmap converts the `plan2.md` architecture into a one-week executable sequence that prioritizes reliability, policy grounding, and demo clarity. The structure front-loads high-risk integrations (fallback correctness, MCP grounding, cyclic audit loop), then layers UI, evaluation, and final hardening before submission packaging.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): planned milestone work
- Decimal phases (2.1, 2.2): urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation and Runtime Baseline** - Project scaffold, data prep, and robust Groq client setup (Completed: 2026-04-05)
- [ ] **Phase 2: Intake Intelligence and Classification Routing** - PII-safe intake plus confidence-aware classification
- [ ] **Phase 3: Root Cause and MCP-Grounded Remediation** - RAG diagnosis and policy tool integration
- [ ] **Phase 4: Response Generation with Compliance Audit Loop** - Drafting, self-correction cycle, and explainability chain
- [ ] **Phase 5: Streamlit HITL Dashboard** - Interactive controls, thread-safe resume, and audit visibility
- [ ] **Phase 6: Evaluation, Fairness, and Robustness** - Metrics, edge-case handling, and reliability tests
- [ ] **Phase 7: Demo Hardening and Submission Package** - Final polish, repeatability checks, and delivery assets

## Phase Details

### Phase 1: Foundation and Runtime Baseline
**Goal**: Establish deterministic foundations for data, model routing, and local execution.
**Depends on**: Nothing (first phase)
**Requirements**: [DATA-01, DATA-02, AGT-01, OPS-01]
**Success Criteria** (what must be TRUE):
1. Team can run setup and execute one successful structured Groq call locally.
2. Sample dataset and vector seed artifacts are reproducibly generated.
3. Fallback chain behavior is verified for retry and model fallback paths.
**Plans**: 3 plans

Plans:
- [x] 01-01: Initialize project structure, environment files, and setup commands
- [x] 01-02: Implement Groq client abstraction with fallback and token tracking
- [x] 01-03: Build dataset sampling and offline vector seeding scripts

### Phase 2: Intake Intelligence and Classification Routing
**Goal**: Build safe intake processing and reliable first-step routing.
**Depends on**: Phase 1
**Requirements**: [DATA-04, FLOW-01, FLOW-02, AGT-02]
**Success Criteria** (what must be TRUE):
1. Complaint intake is PII-scrubbed before any model interaction.
2. Classifier returns schema-valid JSON with confidence values.
3. Low-confidence complaints reliably route to human review interrupt.
**Plans**: 3 plans

Plans:
- [ ] 02-01: Implement PII scrubber and optional mock OCR text merge
- [ ] 02-02: Build classifier agent and schema validation/retry behavior
- [ ] 02-03: Add confidence-based routing logic and interrupt handling

### Phase 3: Root Cause and MCP-Grounded Remediation
**Goal**: Deliver diagnosis plus policy-grounded remediation recommendations.
**Depends on**: Phase 2
**Requirements**: [AGT-03, AGT-04, FLOW-05]
**Success Criteria** (what must be TRUE):
1. Root-cause outputs include evidence from retrieved similar cases.
2. Remediator calls MCP tool to fetch SLA guidance before proposing action.
3. Node-level outputs are logged to SQLite with consistent structure.
**Plans**: 3 plans

Plans:
- [ ] 03-01: Implement vector retrieval and root-cause agent behavior
- [ ] 03-02: Implement FastMCP server and remediator MCP client integration
- [ ] 03-03: Wire audit logger hooks across active graph nodes

### Phase 4: Response Generation with Compliance Audit Loop
**Goal**: Produce response drafts that can self-correct under compliance review.
**Depends on**: Phase 3
**Requirements**: [AGT-05, AGT-06, AGT-07, FLOW-03]
**Success Criteria** (what must be TRUE):
1. Response writer generates customer-ready draft output.
2. Auditor fail verdict loops back to writer with critique context.
3. Explainability output summarizes decisions from key stages.
**Plans**: 3 plans

Plans:
- [ ] 04-01: Implement response writer agent and guardrails
- [ ] 04-02: Implement auditor agent and cyclic routing edge logic
- [ ] 04-03: Implement explainer agent and state critique/history persistence

### Phase 5: Streamlit HITL Dashboard
**Goal**: Expose pipeline behavior and controls through a stable demo UI.
**Depends on**: Phase 4
**Requirements**: [DATA-03, UI-01, UI-02, UI-03, UI-04, UI-05]
**Success Criteria** (what must be TRUE):
1. User can run free-text and golden demo complaints from the UI.
2. Pipeline view surfaces stage status, model choice, latency, and token usage.
3. Human actions (approve/edit/reject) resume the same thread correctly.
**Plans**: 3 plans

Plans:
- [ ] 05-01: Build core Streamlit screens for input, outputs, and golden demos
- [ ] 05-02: Add pipeline telemetry cards and audit trail tab
- [ ] 05-03: Implement HITL controls with session-state thread continuity

### Phase 6: Evaluation, Fairness, and Robustness
**Goal**: Quantify quality and improve resilience for demo reliability.
**Depends on**: Phase 5
**Requirements**: [FLOW-04, EVAL-01, EVAL-02, OPS-02]
**Success Criteria** (what must be TRUE):
1. Evaluation script reports classification metrics on held-out set.
2. Fairness metrics are computed and displayed for selected groups.
3. Automated tests validate fallback behavior and critical graph transitions.
**Plans**: 3 plans

Plans:
- [ ] 06-01: Build evaluation harness for accuracy and quality metrics
- [ ] 06-02: Add fairness computation and dashboard surfacing
- [ ] 06-03: Add edge-case handling and targeted reliability tests

### Phase 7: Demo Hardening and Submission Package
**Goal**: Lock demo reliability and produce final deliverables.
**Depends on**: Phase 6
**Requirements**: [EVAL-03, OPS-03, OPS-04]
**Success Criteria** (what must be TRUE):
1. Golden demo set passes three consecutive end-to-end runs.
2. Submission documents clearly explain architecture, setup, and usage.
3. Team has a backup demo recording and scripted presentation flow.
**Plans**: 2 plans

Plans:
- [ ] 07-01: Execute final hardening pass, caching, and golden-run verification
- [ ] 07-02: Produce submission package, README polish, and backup recording

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation and Runtime Baseline | 3/3 | Complete | 2026-04-05 |
| 2. Intake Intelligence and Classification Routing | 0/3 | Not started | - |
| 3. Root Cause and MCP-Grounded Remediation | 0/3 | Not started | - |
| 4. Response Generation with Compliance Audit Loop | 0/3 | Not started | - |
| 5. Streamlit HITL Dashboard | 0/3 | Not started | - |
| 6. Evaluation, Fairness, and Robustness | 0/3 | Not started | - |
| 7. Demo Hardening and Submission Package | 0/2 | Not started | - |
