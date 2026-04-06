# Requirements: FinComplaint AI

**Defined:** 2026-04-05
**Core Value:** Turn an incoming complaint into a compliant, explainable recommended action in minutes at zero infrastructure cost.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Data and Knowledge Base

- [x] **DATA-01**: Team can download and sample CFPB complaints into a reproducible 10K narrative dataset.
- [x] **DATA-02**: System can precompute embeddings for a 5K complaint subset using `all-MiniLM-L6-v2` via offline batch script.
- [ ] **DATA-03**: System includes five curated golden demo complaints that can be loaded on demand.
- [x] **DATA-04**: Intake pipeline can append extracted text from mock receipt documents before classification.

### Pipeline and State

- [x] **FLOW-01**: System scrubs PII from complaint text before any LLM call.
- [x] **FLOW-02**: Graph routes low-confidence classification results to human review interrupt flow.
- [x] **FLOW-03**: Graph state stores message history so auditor critiques can influence response rewrites.
- [ ] **FLOW-04**: Pipeline handles empty input, long complaints, and ambiguous text without crashing.
- [x] **FLOW-05**: Every node writes structured decision logs to SQLite with timestamp and model metadata.

### Agent Intelligence

- [x] **AGT-01**: LLM client retries 429s with backoff and falls back `llama-3.3-70b-versatile -> mixtral-8x7b-32768 -> llama-3.1-8b-instant`.
- [x] **AGT-02**: Classifier returns strict JSON with `product_type`, `issue_type`, `severity`, `compliance_risk`, and `confidence`.
- [x] **AGT-03**: Root-cause agent uses top-5 retrieved similar complaints as context.
- [x] **AGT-04**: Remediator calls MCP tool `get_sla_requirements(issue_type, state_code)` before proposing action.
- [x] **AGT-05**: Response writer generates customer-facing draft with clear resolution statement and safe tone.
- [x] **AGT-06**: Compliance auditor evaluates response and routes fail cases back to response writer.
- [x] **AGT-07**: Explainer produces concise rationale chain for classification, diagnosis, remediation, and final response.

### User Interface

- [ ] **UI-01**: Streamlit app accepts raw complaint input and golden demo selection.
- [ ] **UI-02**: UI displays pipeline stage status including model used, token usage, and latency.
- [ ] **UI-03**: Human reviewer can approve, edit, or reject remediation and resume same graph thread.
- [ ] **UI-04**: Audit tab shows ordered decision events with timestamps and model versions.
- [ ] **UI-05**: Token budget widget shows daily free-tier usage status.

### Evaluation and Reliability

- [ ] **EVAL-01**: Team can run held-out classification evaluation and report macro F1.
- [ ] **EVAL-02**: Team can compute disparate impact ratios across selected complaint groups.
- [ ] **EVAL-03**: Golden demos pass three consecutive full runs without critical failure.

### Operations and Delivery

- [x] **OPS-01**: Repository includes setup and run steps that let a new teammate start the system locally.
- [ ] **OPS-02**: Automated tests cover fallback routing, schema validation, and core graph transitions.
- [ ] **OPS-03**: Submission package includes architecture summary, setup instructions, and demo flow description.
- [ ] **OPS-04**: Team has a short recorded backup demo and script for presentation-day contingency.

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Platform and Product Expansion

- **PLAT-01**: Replace local SQLite with managed Postgres and retention policies.
- **PLAT-02**: Replace local ChromaDB with managed vector infrastructure.
- **PLAT-03**: Add production authentication, RBAC, and audit access controls.
- **PLAT-04**: Introduce full OCR/document ingestion pipeline beyond mock receipts.
- **PLAT-05**: Add provider-agnostic LLM abstraction for multi-vendor resiliency.
- **PLAT-06**: Add advanced observability dashboarding and alerting.
- **PLAT-07**: Add model-comparison experiments (e.g., reasoning benchmark modes).

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Enterprise deployment (Kubernetes, autoscaling) | Not required for one-week MVP and demo goals |
| End-user mobile apps | Web demo is sufficient for current validation |
| Real legal compliance guarantees | Product is decision support, not legal automation |
| Fully autonomous resolution execution | Human approval remains required for risky actions |
| Cross-provider LLM orchestration in v1 | Adds integration overhead and test complexity |
| Real-time websocket visualization | Lower priority than core reliability and explainability |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-01 | Phase 1 | Complete (2026-04-05) |
| DATA-02 | Phase 1 | Complete (2026-04-05) |
| AGT-01 | Phase 1 | Complete (2026-04-05) |
| OPS-01 | Phase 1 | Complete (2026-04-05) |
| DATA-04 | Phase 2 | Complete (2026-04-05) |
| FLOW-01 | Phase 2 | Complete (2026-04-05) |
| FLOW-02 | Phase 2 | Complete (2026-04-05) |
| AGT-02 | Phase 2 | Complete (2026-04-05) |
| AGT-03 | Phase 3 | Complete |
| AGT-04 | Phase 3 | Complete |
| FLOW-05 | Phase 3 | Complete |
| AGT-05 | Phase 4 | Complete (2026-04-05) |
| AGT-06 | Phase 4 | Complete (2026-04-05) |
| AGT-07 | Phase 4 | Complete (2026-04-05) |
| FLOW-03 | Phase 4 | Complete (2026-04-05) |
| DATA-03 | Phase 5 | Pending |
| UI-01 | Phase 5 | Pending |
| UI-02 | Phase 5 | Pending |
| UI-03 | Phase 5 | Pending |
| UI-04 | Phase 5 | Pending |
| UI-05 | Phase 5 | Pending |
| FLOW-04 | Phase 6 | Pending |
| EVAL-01 | Phase 6 | Pending |
| EVAL-02 | Phase 6 | Pending |
| OPS-02 | Phase 6 | Pending |
| EVAL-03 | Phase 7 | Pending |
| OPS-03 | Phase 7 | Pending |
| OPS-04 | Phase 7 | Pending |

**Coverage:**
- v1 requirements: 28 total
- Mapped to phases: 28
- Unmapped: 0

---
*Requirements defined: 2026-04-05*
*Last updated: 2026-04-05 after Phase 4 completion*
