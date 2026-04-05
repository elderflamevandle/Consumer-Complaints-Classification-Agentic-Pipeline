# Architecture Research

**Domain:** Agentic AI complaint resolution platform for consumer finance operations
**Researched:** 2026-04-05
**Confidence:** MEDIUM

## Standard Architecture

### System Overview

```
+-------------------------------------------------------------+
|                    Presentation Layer                       |
|  Streamlit app (input, pipeline view, HITL controls)        |
+-----------------------------+-------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|                 Orchestration Layer (LangGraph)             |
| scrub -> classify -> root_cause -> remediate -> response    |
|                     -> audit loop -> explain                 |
|                with conditional edges + interrupts           |
+-----------------------------+-------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|                    Agent + Tool Layer                       |
|  Groq LLM client | MCP client | PII scrubber | vector search|
+-----------------------------+-------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|                        Data Layer                           |
| SQLite audit log | ChromaDB vectors | local datasets/config |
+-----------------------------+-------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|                   External Interfaces                        |
| Groq API | MCP server (SLA rules)                           |
+-------------------------------------------------------------+
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| Intake + preprocessing | Prepare complaint text and remove PII | Presidio + optional OCR extraction |
| Classifier agent | Product/issue/risk classification with confidence | 8B model with strict JSON schema |
| Root-cause agent | Diagnose complaint root causes with evidence | 70B model + top-k retrieval context |
| Remediator agent | Produce policy-grounded recommended action | 70B model + MCP SLA tool call |
| Response writer agent | Draft user-facing resolution communication | 70B model with policy constraints |
| Compliance auditor agent | Detect unsafe/non-compliant response output | 8B model, fail/pass plus critique |
| Explainer agent | Summarize why decisions were made | 8B model into audit-friendly summary |
| UI runtime | Human decision controls and observability | Streamlit `session_state` thread config |

## Recommended Project Structure

```
fincomplaint-ai/
|-- mcp_server/                 # External policy tool server
|-- src/
|   |-- llm/                    # Model routing, retries, fallback
|   |-- agents/                 # One file per agent role
|   |-- graph/                  # State schema + pipeline graph
|   |-- tools/                  # PII, vector search, OCR, audit logger
|   |-- schemas/                # Pydantic output contracts
|   `-- eval/                   # Fairness and quality evaluation scripts
|-- app/                        # Streamlit UI
|-- scripts/                    # Offline jobs (seed vectors, generate demos)
`-- tests/                      # Routing, fallback, parser, and flow tests
```

### Structure Rationale

- **`src/agents/` isolation:** Keeps prompt/schema coupling localized per behavior.
- **`src/graph/` centralization:** Prevents hidden routing logic spread across modules.
- **`scripts/` for heavy preprocessing:** Avoids blocking runtime with expensive batch jobs.

## Architectural Patterns

### Pattern 1: Stateful Graph with Interrupt Gates

**What:** Orchestrate deterministic node transitions with conditional branching.
**When to use:** Multi-step reasoning with compliance or human-approval gates.
**Trade-offs:** Great observability and control, but more state management complexity.

**Example:**
```python
if classification.confidence < 0.7:
    return "human_review"
return "root_cause"
```

### Pattern 2: Tool-Grounded Agent Decisions

**What:** Require external tool evidence for specific decisions (MCP for SLA).
**When to use:** Domain outputs must reference policy or factual constraints.
**Trade-offs:** Better trust and reproducibility, but added integration failure surface.

**Example:**
```python
sla = mcp_client.call_tool("get_sla_requirements", issue_type, state_code)
```

### Pattern 3: Schema-First LLM IO

**What:** Validate every model output against explicit schemas.
**When to use:** Downstream logic relies on structured data.
**Trade-offs:** Additional retries/re-prompts, but major reduction in brittle parsing.

## Data Flow

### Request Flow

```
User complaint
  -> preprocess (PII + optional OCR)
  -> classify
  -> retrieve similar cases
  -> root cause
  -> remediate (with MCP SLA)
  -> write response
  -> audit response (loop until pass or max retries)
  -> explain + persist logs
  -> return UI result
```

### State Management

```
LangGraph state object
  <-> node outputs
  <-> audit logger
  <-> Streamlit session thread config
```

### Key Data Flows

1. **Policy grounding flow:** Remediator fetches SLA context before proposing action.
2. **Safety correction flow:** Auditor feedback appends critique that writer must address.
3. **Traceability flow:** Every node emits structured event into SQLite audit table.

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 0-100 daily complaints | Keep fully local (SQLite + local ChromaDB) |
| 100-5k daily complaints | Move vector store and DB to managed services |
| 5k+ daily complaints | Introduce async job workers and API service split |

### Scaling Priorities

1. **First bottleneck:** Embedding/retrieval and synchronous agent latency.
2. **Second bottleneck:** Stateful UI orchestration under concurrent sessions.

## Anti-Patterns

### Anti-Pattern 1: Single Prompt "Mega-Agent"

**What people do:** Collapse classification, remediation, and response into one call.
**Why it's wrong:** Hard to debug, weak control points, no clear risk boundaries.
**Do this instead:** Keep specialized agents with explicit handoff contracts.

### Anti-Pattern 2: UI-Driven Business Logic

**What people do:** Put routing and state mutation directly inside Streamlit callbacks.
**Why it's wrong:** Reruns reset state and create non-deterministic behavior.
**Do this instead:** Keep domain logic inside graph and use UI as controller/view.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Groq API | OpenAI-compatible chat completions | Use JSON mode and deterministic temperature |
| MCP server | Tool discovery + tool invocation | Keep protocol boundary explicit for demo credibility |
| HuggingFace dataset | Offline download/sampling script | Pin sample generation logic for reproducibility |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `graph` <-> `agents` | Typed state payloads | Avoid direct cross-agent imports |
| `agents` <-> `tools` | Function/tool calls | Keep tool adapters thin and deterministic |
| `app` <-> `graph` | Thread config + event payloads | Persist session IDs to resume interrupts safely |

## Sources

- `f:/Agentic_Hackathon/plan2.md`
- `f:/Agentic_Hackathon/plan.md`
- `.planning/PROJECT.md`

---
*Architecture research for: Agentic AI complaint resolution platform for consumer finance operations*
*Researched: 2026-04-05*
