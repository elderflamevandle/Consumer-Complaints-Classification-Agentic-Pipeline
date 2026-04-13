# FinComplaint AI — Code Flow

Complete execution path for a financial complaint through the multi-agent LangGraph pipeline.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Entry Points                             │
│                                                                 │
│   run_pipeline.py (CLI)        app/api.py (FastAPI HTTP)        │
│        │                            │                           │
│        │  POST /api/v1/complaints   │  GET /api/v1/health       │
└────────┼────────────────────────────┼───────────────────────────┘
         │                            │
         └──────────────┬─────────────┘
                        ▼
              src/graph/pipeline.py
              build_graph() → _GRAPH singleton
              run_complaint(text, state_code, thread_id)
                        │
                        ▼
              src/graph/langgraph_state.py
              PipelineState (TypedDict)
```

---

## LangGraph Node Execution Order

```
START
  │
  ▼
┌─────────────────────────────────────────────────────────────┐
│  STAGE 1 — Complaint Ingress                                │
│                                                             │
│  intake_node                                                │
│  └── src/intake/pipeline.py                                 │
│      └── src/intake/pii.py          ← scrubs PII           │
│          (SSN → [SSN], names, etc.)                        │
│      └── src/schemas/intake.py      ← typed output         │
└─────────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────────┐
│  STAGE 2 — Classification                                   │
│                                                             │
│  product_classifier_node                                    │
│  └── src/agents/product_classifier.py                       │
│      └── src/schemas/taxonomy.py    ← CFPB product enum    │
│                                                             │
│  issue_classifier_node                                      │
│  └── src/agents/issue_classifier.py                         │
│      └── src/schemas/classification.py                      │
│          (product_type, issue_type, severity: CRITICAL/...) │
└─────────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────────┐
│  STAGE 3 — Diagnosis                                        │
│                                                             │
│  root_cause_node                                            │
│  └── src/agents/root_cause.py                               │
│      └── src/tools/vector_search.py ← RAG: similar cases   │
│          └── src/tools/hf_embedding_api.py  ← HF embeddings│
│              └── chroma_db/         ← ChromaDB store        │
│      └── src/schemas/root_cause.py  ← typed output         │
│                                                             │
│  remediator_node                                            │
│  └── src/agents/remediator.py                               │
│      └── src/tools/mcp_policy_client.py ← SLA lookups      │
│          └── [subprocess] → legal_knowledge_mcp/bridge.py  │
│              ├── live: GovInfo API + Open States API        │
│              └── mock: LEGAL_MCP_USE_MOCK_FALLBACK=1        │
└─────────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────────┐
│  STAGE 4 — Response Generation (Actor-Critic Loop)          │
│                                                             │
│  response_writer_node  ◄─────────────────────┐             │
│  └── src/agents/writer.py                    │ needs_rewrite│
│      └── src/schemas/response.py             │ (max 2x)    │
│          (resolution_statement, action_steps, │             │
│           policy_citation_labels, ...)        │             │
│                │                             │             │
│                ▼                             │             │
│  response_auditor_node ──────────────────────┘             │
│  └── src/agents/auditor.py                                  │
│      └── src/schemas/auditor.py                             │
│          verdict: "approved" | "needs_rewrite"              │
│          MAX_REWRITE_ATTEMPTS = 2 (force-approve after)     │
└─────────────────────────────────────────────────────────────┘
  │ (approved)
  ▼
┌─────────────────────────────────────────────────────────────┐
│  STAGE 5 — Compliance Explanation                           │
│                                                             │
│  explainer_node                                             │
│  └── src/agents/explainer.py                                │
│      └── src/schemas/explainer.py   ← audit trail          │
│      └── src/tools/audit_logger.py  ← structured logging   │
└─────────────────────────────────────────────────────────────┘
  │
  ▼
END → PipelineState returned to caller
```

---

## Module Map

### Entry Points

| File | Purpose |
|------|---------|
| `run_pipeline.py` | CLI runner — builds graph, calls `run_complaint()`, prints results |
| `app/api.py` | FastAPI HTTP layer — builds graph once at startup via `@app.on_event("startup")` |

### Graph Layer (`src/graph/`)

| File | Purpose |
|------|---------|
| `pipeline.py` | Wires all nodes into the LangGraph DAG; `build_graph()` / `get_graph()` / `run_complaint()` |
| `nodes.py` | One function per pipeline node; each wraps an agent singleton, measures latency, emits telemetry |
| `langgraph_state.py` | `PipelineState` TypedDict — the shared state flowing through all nodes |
| `state.py` | `RoutingState` — used by interrupts, routing, and response loop modules |
| `routing.py` | `_route_after_auditor()` — conditional edge: `"approved"` → explainer, else → writer |
| `response_loop.py` | `ResponseCycleTrace` — tracks rewrite loop count and cycle history |
| `interrupts.py` | Legacy interrupt infrastructure (`ReviewDecision`, `ReviewInterruptPayload`) |

### Agent Layer (`src/agents/`)

| File | Agent | Input → Output |
|------|-------|----------------|
| `product_classifier.py` | Product Classifier | sanitized complaint → CFPB product type |
| `issue_classifier.py` | Issue Classifier | complaint + product → issue type + severity |
| `root_cause.py` | Root Cause | complaint + classification + similar cases → root cause summary |
| `remediator.py` | Remediator | root cause + policy → SLA deadline + required actions |
| `writer.py` | Response Writer | all prior context → structured customer response draft |
| `auditor.py` | Response Auditor | draft → verdict (`approved` / `needs_rewrite`) + critique items |
| `explainer.py` | Explainer | full pipeline state → compliance audit trail |
| `classifier.py` | (Legacy) Combined classifier — superseded by product/issue split |
| `prompts.py` | Shared prompt templates used across agents |

### Tool Layer (`src/tools/`)

| File | Purpose |
|------|---------|
| `mcp_policy_client.py` | `MCPPolicyClient` — spawns MCP subprocess, calls `get_sla_policy()`, returns `SLAPolicy` |
| `vector_search.py` | `RetrievedCase` — queries ChromaDB for similar past complaints |
| `hf_embedding_api.py` | HuggingFace Inference API embeddings used to index/query ChromaDB |
| `vector_index.py` | ChromaDB collection setup and document indexing |
| `audit_logger.py` | Structured JSON audit log writer |

### Intake Layer (`src/intake/`)

| File | Purpose |
|------|---------|
| `pii.py` | Regex-based PII scrubber — masks SSN, email, phone, names |
| `pipeline.py` | Intake agent: runs PII scrub, builds sanitized complaint object |
| `receipt_merge.py` | Merges any attached receipt/document data into complaint context |

### LLM Layer (`src/llm/`)

| File | Purpose |
|------|---------|
| `client.py` | LLM client abstraction (Groq) — all agents call through this |
| `models.py` | Model name constants and per-agent model config |
| `rate_limiter.py` | Token bucket rate limiter to stay within Groq API limits |

### Schema Layer (`src/schemas/`)

| File | Schema | Fields |
|------|--------|--------|
| `intake.py` | `IntakeResult` | sanitized_text, pii_removed, metadata |
| `taxonomy.py` | `ProductType`, `IssueType` | CFPB-aligned enums |
| `classification.py` | `ClassificationResult` | product_type, issue_type, severity |
| `root_cause.py` | `RootCauseAnalysis` | summary, contributing_factors, evidence |
| `response.py` | `ResponseDraft` | resolution_statement, acknowledgment, findings, action_steps, timeline_next_steps, policy_citation_labels, critique_items_addressed |
| `auditor.py` | `AuditResult` | verdict, critique_items, rewrite_count |
| `explainer.py` | `ExplanationResult` | regulatory_basis, compliance_steps, audit_trail |

### Legal Knowledge MCP (`legal_knowledge_mcp/`)

| File | Purpose |
|------|---------|
| `bridge.py` | Compliance bridge — live GovInfo + Open States APIs by default; mock JSON when `LEGAL_MCP_USE_MOCK_FALLBACK=1` |
| `mcp_server/` | MCP server implementation that `MCPPolicyClient` spawns as a subprocess |

---

## State Object (`PipelineState`)

Every node reads from and writes back to this shared TypedDict:

```
PipelineState
├── complaint_text          str   (raw input)
├── state_code              str   (2-char US state, e.g. "NY")
├── thread_id               str
│
├── intake                  IntakeResult
├── classification          ClassificationResult
├── diagnosis               RootCauseAnalysis
├── remediation             RemediationResult
├── response_draft          ResponseDraft
├── audit_result            AuditResult
├── response_loop_status    str   ("approved" | "needs_rewrite")
├── explanation             ExplanationResult
│
├── stage_telemetry         list[TelemetryRecord]
└── events                  list[str]
```

---

## Telemetry (Per Node)

Every node calls `_telemetry()` which records:

```python
{
    "node":         str,      # node name
    "latency_ms":   float,
    "model":        str,      # last model used by agent
    "tokens":       int,      # last_total_tokens
    "attempts":     int,      # last_llm_attempts
    "used_fallback":bool,
    "timestamp":    str       # ISO-8601
}
```

Appended to `state["stage_telemetry"]` — available on every pipeline response.

---

## Known Gotchas

| Area | Gotcha |
|------|--------|
| MCP Policy Client | Spawns a subprocess — hangs if MCP server is unavailable. Use `LEGAL_MCP_USE_MOCK_FALLBACK=1` for tests. |
| `SLAPolicy` schema | Had `extra='forbid'` — any unexpected field (like `source: "mock_fallback"`) from bridge raises `ValidationError`. Fixed with `extra='ignore'`. |
| State modules | Two parallel state modules coexist: `state.py` (`RoutingState`) for routing/interrupts and `langgraph_state.py` (`PipelineState`) for nodes/pipeline. |
| Auditor loop | `MAX_REWRITE_ATTEMPTS = 2` — after 2 rewrites the auditor force-approves regardless of verdict, preventing infinite loops. |
| NY SLA gap | NY state returns `sla_deadline=None, source=None` from the MCP server — regulatory data for NY is incomplete in the mock database. |

---

## How to Run

```bash
# CLI
uv run python run_pipeline.py

# FastAPI server
uv run uvicorn app.api:app --reload

# With mock MCP (no live API calls)
LEGAL_MCP_USE_MOCK_FALLBACK=1 uv run python run_pipeline.py
```

---

## File Index (Quick Reference)

```
F:/Agentic_Hackathon/
├── run_pipeline.py                    ← CLI entry point
├── app/api.py                         ← FastAPI HTTP entry point
├── src/
│   ├── config.py                      ← Settings (get_settings())
│   ├── agents/
│   │   ├── product_classifier.py
│   │   ├── issue_classifier.py
│   │   ├── root_cause.py
│   │   ├── remediator.py
│   │   ├── writer.py
│   │   ├── auditor.py
│   │   ├── explainer.py
│   │   └── prompts.py
│   ├── graph/
│   │   ├── pipeline.py                ← graph wiring
│   │   ├── nodes.py                   ← node functions
│   │   ├── langgraph_state.py         ← PipelineState
│   │   ├── state.py                   ← RoutingState
│   │   ├── routing.py
│   │   ├── response_loop.py
│   │   └── interrupts.py
│   ├── intake/
│   │   ├── pipeline.py
│   │   ├── pii.py
│   │   └── receipt_merge.py
│   ├── tools/
│   │   ├── mcp_policy_client.py
│   │   ├── vector_search.py
│   │   ├── hf_embedding_api.py
│   │   ├── vector_index.py
│   │   └── audit_logger.py
│   ├── schemas/
│   │   ├── taxonomy.py
│   │   ├── classification.py
│   │   ├── intake.py
│   │   ├── root_cause.py
│   │   ├── response.py
│   │   ├── auditor.py
│   │   └── explainer.py
│   └── llm/
│       ├── client.py
│       ├── models.py
│       └── rate_limiter.py
└── legal_knowledge_mcp/
    └── bridge.py                      ← compliance data bridge
```
