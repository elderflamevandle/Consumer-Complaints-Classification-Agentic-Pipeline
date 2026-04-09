# Architecture Plan: Decoupled Application with Backend API

**Date:** April 7, 2026  
**Status:** Planning  
**Owner:** AI Backend Team  
**Target Delivery:** Phase 5-6 of New App Development

---

## Executive Summary

This document outlines the architecture for a **separate full-stack application** (frontend + backend) that will:
- Use **fincomplaint-ai** as a reusable Python library backend
- Expose complaint pipeline via **REST + WebSocket APIs**
- Deliver a modern **React/Next.js web UI** for operators and judges
- Support **multi-user, distributed deployment** (local dev to cloud production)
- Maintain **thread-safe, deterministic complaint processing**

The design decouples the core pipeline from presentation, enabling flexible deployment and multiple frontend implementations (web, mobile, CLI).

---

## Current State

**fincomplaint-ai (this repository):**
- ✅ 4 complete phases (Intake → Classification → Root Cause → Audit Loop)
- ✅ Groq LLM integration with smart fallback chain
- ✅ MCP-grounded remediation
- ✅ SQLite audit logging at node level
- ❌ Not exposed as a library
- ❌ No REST/WebSocket API
- ❌ No multi-user thread management

**New Application (separate repo):**
- ❌ Does not exist yet
- Will import fincomplaint-ai as a library
- Will provide REST + WebSocket surface for frontends

---

## Architecture Overview

### System Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      End User (Browser)                         │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 │ HTTP / WebSocket
                 │
┌────────────────▼────────────────────────────────────────────────┐
│                   React / Next.js Frontend                       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Complaint Form │ Pipeline View │ Review Panel │ Audit Tab │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 │ REST API + WebSocket
                 │
┌────────────────▼────────────────────────────────────────────────┐
│                    FastAPI Backend Server                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Routes │ Schemas │ WebSocket │ Auth │ Rate Limit │ Life │   │
│  └──────────────────────────────────────────────────────────┘   │
│                         ▲                                        │
│                         │ Imports                                │
├─────────────────────────┼────────────────────────────────────────┤
│                    Orchestrator Layer                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ ComplaintOrchestrator                                     │   │
│  │  ├─ Thread Management (in-memory / Redis)                │   │
│  │  ├─ Pipeline Execution (wraps LangGraph)                 │   │
│  │  ├─ HITL Review Handling                                 │   │
│  │  └─ State Snapshots & Persistence                        │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────┬─────────────────────────────────────────────────────┘
             │
             │ Imports fincomplaint_ai library
             │
┌────────────▼─────────────────────────────────────────────────────┐
│                  fincomplaint-ai Library                         │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ build_complaint_graph()                                   │   │
│  │ ├─ PII Scrubber                                          │   │
│  │ ├─ Classifier Agent                                      │   │
│  │ ├─ Root Cause Agent (Vector RAG)                         │   │
│  │ ├─ Remediator (MCP Policy Tool)                          │   │
│  │ ├─ Response Writer                                       │   │
│  │ ├─ Compliance Auditor                                    │   │
│  │ └─ Explainer                                             │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Tools & Services                                          │   │
│  │ ├─ LLM Client (Groq with fallback)                       │   │
│  │ ├─ Vector Store (ChromaDB)                               │   │
│  │ ├─ Audit Logger (SQLite)                                 │   │
│  │ ├─ MCP Client (SLA Policies)                             │   │
│  │ └─ Rate Limiter (Token Budget)                           │   │
│  └──────────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────┐
│                      External Services                            │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                 │
│  │ Groq API    │ │ MCP Server  │ │ Redis/      │                 │
│  │             │ │ (SLA/Regs)  │ │ Postgres    │                 │
│  └─────────────┘ └─────────────┘ └─────────────┘                 │
└───────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Owns | Primary Interface |
|-----------|------|-------------------|
| **Frontend (React/Next.js)** | UI state, rendering, user events | HTTP requests, WebSocket messages |
| **Backend (FastAPI)** | Thread routing, API schema enforcement, session mgmt | REST endpoints, WebSocket handlers |
| **Orchestrator** | Pipeline execution, HITL threading model, state snapshots | Typed async method calls |
| **fincomplaint-ai Library** | Core complaint processing, audit logging | Python classes/functions |
| **External Services** | LLM inference, policy lookup, persistence | REST APIs, database connections |

---

## Refactoring fincomplaint-ai to be Library-Ready

### Step 1: Create Public API Export

**File:** `src/__init__.py`

```python
"""FinComplaint AI - Complaint triage and remediation library."""

from src.graph.routing import build_complaint_graph
from src.api import ComplaintOrchestrator

__all__ = [
    "build_complaint_graph",
    "ComplaintOrchestrator",
]

__version__ = "0.1.0"
```

### Step 2: Add Orchestrator Class

**File:** `src/api.py` (NEW)

```python
"""Async orchestrator for complaint pipeline execution."""

from typing import Optional, Dict, Any, AsyncIterator
from dataclasses import dataclass, field
import uuid
from datetime import datetime

from src.graph.state import RoutingState
from src.graph.routing import build_complaint_graph

@dataclass
class ThreadSnapshot:
    """Immutable snapshot of pipeline state for API responses."""
    thread_id: str
    complaint_source: str  # 'manual' or demo_id
    current_stage: str  # 'intake', 'classify', 'root_cause', etc.
    status: str  # 'pending', 'interrupted', 'complete', 'error'
    stages: Dict[str, Any] = field(default_factory=dict)
    review_state: Optional[Dict[str, Any]] = None
    response_draft: Optional[str] = None
    explanation: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

class ComplaintOrchestrator:
    """Orchestrates complaint processing with thread safety and state management."""
    
    def __init__(self, persist_dir: str = "./.complaint_threads"):
        self.graph = build_complaint_graph()
        self.threads: Dict[str, RoutingState] = {}
        self.snapshots: Dict[str, ThreadSnapshot] = {}
        self.persist_dir = persist_dir
    
    async def submit_complaint(
        self, 
        complaint_text: str, 
        source: str = "manual"
    ) -> str:
        """Submit a complaint and return thread_id."""
        thread_id = str(uuid.uuid4())
        
        # Initialize state
        state = RoutingState(
            raw_complaint=complaint_text,
            thread_id=thread_id,
            source=source,
        )
        
        # Execute pipeline (returns on first interrupt or completion)
        updated_state = await self._execute_pipeline(state)
        
        # Store snapshot
        self.threads[thread_id] = updated_state
        self.snapshots[thread_id] = self._build_snapshot(updated_state)
        
        return thread_id
    
    async def get_status(self, thread_id: str) -> ThreadSnapshot:
        """Get current pipeline status for a thread."""
        if thread_id not in self.threads:
            raise ValueError(f"Thread {thread_id} not found")
        
        return self.snapshots[thread_id]
    
    async def submit_review_action(
        self,
        thread_id: str,
        action: str,  # 'approve', 'edit', 'reject'
        edit_text: Optional[str] = None,
    ) -> ThreadSnapshot:
        """Handle human review action and resume pipeline."""
        if thread_id not in self.threads:
            raise ValueError(f"Thread {thread_id} not found")
        
        state = self.threads[thread_id]
        
        # Apply review action to state
        if action == "approve":
            state.reviewer_action = "approve"
        elif action == "reject":
            state.reviewer_action = "reject"
        elif action == "edit":
            state.reviewer_action = "edit"
            state.reviewer_edit_text = edit_text
        
        # Resume pipeline execution
        updated_state = await self._execute_pipeline(state)
        
        # Update snapshot
        self.threads[thread_id] = updated_state
        self.snapshots[thread_id] = self._build_snapshot(updated_state)
        
        return self.snapshots[thread_id]
    
    async def stream_updates(
        self, 
        thread_id: str
    ) -> AsyncIterator[Dict[str, Any]]:
        """Stream live pipeline updates for WebSocket subscribers."""
        if thread_id not in self.threads:
            raise ValueError(f"Thread {thread_id} not found")
        
        # This will be called continuously by the WebSocket handler
        # Yield snapshots at key stage transitions
        last_stage = None
        
        while True:
            current_stage = self.snapshots[thread_id].current_stage
            if current_stage != last_stage:
                yield self._snapshot_to_dict(self.snapshots[thread_id])
                last_stage = current_stage
            
            # Check if complete
            if self.snapshots[thread_id].status in ["complete", "error"]:
                break
            
            await asyncio.sleep(0.5)
    
    async def get_audit_events(self, thread_id: str) -> list:
        """Fetch ordered audit events from SQLite."""
        # Queries audit_logger.py for this thread
        return fetch_events_for_thread(thread_id)
    
    # Private helpers
    
    async def _execute_pipeline(self, state: RoutingState) -> RoutingState:
        """Execute/resume pipeline, returns on interrupt or completion."""
        # Invokes LangGraph with state
        # Returns updated state
        pass
    
    def _build_snapshot(self, state: RoutingState) -> ThreadSnapshot:
        """Convert RoutingState to API-safe ThreadSnapshot."""
        pass
    
    def _snapshot_to_dict(self, snapshot: ThreadSnapshot) -> Dict[str, Any]:
        """Convert snapshot to JSON-serializable dict."""
        pass
```

### Step 3: Update pyproject.toml

Add optional dependencies for FastAPI:

```toml
[project.optional-dependencies]
api = [
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "redis>=5.0.0",
]
```

### Step 4: Documentation

**File:** `.planning/API_CONTRACT.md` (NEW)

Clear documentation for library consumers:
- How to instantiate `ComplaintOrchestrator`
- Thread model (async, blocking, concurrent limits)
- Required environment setup (GROQ_API_KEY, etc.)
- Example integration code

---

## New Application Repository Structure

### Repository Layout

```
fincomplaint-app/                          [New repository]
│
├── backend/                               [Python FastAPI backend]
│   ├── __init__.py
│   ├── main.py                           # FastAPI app entrypoint
│   ├── config.py                         # Environment + settings
│   ├── core/
│   │   ├── __init__.py
│   │   └── orchestrator.py               # Wraps fincomplaint-ai
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py                     # HTTP endpoint handlers
│   │   ├── schemas.py                    # Pydantic models
│   │   └── websocket.py                  # WebSocket handlers
│   ├── models/
│   │   ├── __init__.py
│   │   └── thread.py                     # Thread persistence models
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth.py                       # Auth/API key validation
│   │   └── persistence.py                # Thread state storage
│   └── tests/
│       ├── __init__.py
│       ├── test_orchestrator.py
│       ├── test_routes.py
│       └── test_websocket.py
│
├── frontend/                              [React/Next.js app]
│   ├── app/
│   │   ├── layout.tsx                    # Root layout
│   │   ├── complaint/
│   │   │   ├── page.tsx                  # Main complaint page
│   │   │   └── loading.tsx               # Loading skeleton
│   │   └── audit/
│   │       └── page.tsx                  # Audit history tab
│   ├── components/
│   │   ├── ComplaintForm.tsx             # Input form
│   │   ├── PipelineView.tsx              # Stage visualization
│   │   ├── ReviewPanel.tsx               # HITL controls
│   │   ├── AuditTable.tsx                # Event history
│   │   └── BudgetWidget.tsx              # Token usage
│   ├── hooks/
│   │   ├── useComplaint.ts               # API client hook
│   │   ├── useWebSocket.ts               # WebSocket management
│   │   └── useReview.ts                  # HITL action handler
│   ├── types/
│   │   └── api.ts                        # API type definitions
│   ├── lib/
│   │   └── api-client.ts                 # HTTP + WebSocket client
│   ├── styles/
│   │   └── globals.css
│   ├── public/
│   │   └── [assets]
│   └── tests/
│       ├── __tests__/
│       │   ├── ComplaintForm.test.tsx
│       │   └── PipelineView.test.tsx
│       └── e2e/
│           └── complaint-flow.spec.ts
│
├── shared/                               [Shared contracts]
│   ├── api.ts                            # Request/response DTOs
│   ├── constants.ts                      # Shared constants
│   └── types.ts                          # Shared type definitions
│
├── infra/                                [Deployment configs]
│   ├── docker-compose.yml                # Local dev stack
│   ├── Dockerfile.backend                # Backend image
│   ├── Dockerfile.frontend               # Frontend image
│   ├── k8s/                              # Kubernetes manifests
│   │   ├── deployment.yaml
│   │   └── service.yaml
│   └── nginx.conf                        # Reverse proxy (prod)
│
├── .env.example
├── .dockerignore
├── .gitignore
├── docker-compose.yml
├── Makefile
├── requirements.txt                      # Python deps
├── package.json                          # Node.js deps
├── pyproject.toml                        # Python tooling config
├── tsconfig.json                         # TypeScript config
├── next.config.js                        # Next.js config
├── pytest.ini                            # Python testing config
├── jest.config.js                        # JavaScript testing config
│
├── docs/                                 [Documentation]
│   ├── ARCHITECTURE.md
│   ├── API.md
│   ├── DEPLOYMENT.md
│   └── DEVELOPMENT.md
│
└── README.md
```

---

## REST API Specification

### Base URL
```
http://localhost:8000/api/v1          (local dev)
https://api.complaints.example.com    (production)
```

### Authentication
- **v1 (MVP):** No authentication (internal demo only)
- **v2 (Future):** Bearer token (API key format: "cpt_xxxxxxxxxxxxx")

### Endpoints

#### 1. Submit Complaint

```http
POST /v1/complaints
Content-Type: application/json

{
  "complaint_text": "I was charged twice for my purchase...",
  "demo_id": null           // Optional: load golden demo instead
}
```

**Response (202 Accepted):**
```json
{
  "thread_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "created_at": "2026-04-07T10:30:00Z",
  "websocket_url": "ws://localhost:8000/ws/complaints/550e8400-..."
}
```

**Errors:**
- `400 Bad Request` - Invalid complaint_text or demo_id
- `429 Too Many Requests` - Rate limit exceeded

---

#### 2. Get Complaint Status

```http
GET /v1/complaints/{thread_id}
```

**Response (200 OK):**
```json
{
  "thread_id": "550e8400-e29b-41d4-a716-446655440000",
  "complaint_source": "manual",
  "current_stage": "auditor_loop",
  "status": "interrupted",
  "stages": {
    "intake": {
      "status": "complete",
      "model": "local-presidio",
      "latency_ms": 42,
      "tokens_used": 0
    },
    "classifier": {
      "status": "complete",
      "model": "llama-3.3-70b-versatile",
      "latency_ms": 1247,
      "tokens_used": 312,
      "output": {
        "product_type": "credit_card",
        "issue_type": "billing_error",
        "severity": "high",
        "compliance_risk": "medium",
        "confidence": 0.92
      }
    },
    "root_cause": {
      "status": "complete",
      "model": "llama-3.3-70b-versatile",
      "latency_ms": 2103,
      "tokens_used": 847,
      "evidence": [...]
    },
    "remediator": {
      "status": "complete",
      "model": "llama-3.3-70b-versatile",
      "latency_ms": 1893,
      "tokens_used": 521,
      "recommendation": "Issue refund of $150 with 6% interest..."
    },
    "writer": {
      "status": "complete",
      "model": "llama-3.3-70b-versatile",
      "latency_ms": 2041,
      "tokens_used": 634,
      "response_draft": "Dear Customer, We sincerely apologize..."
    },
    "auditor": {
      "status": "pending",
      "model": "llama-3.1-8b-instant",
      "latency_ms": 0,
      "tokens_used": 0
    }
  },
  "review_state": {
    "reason": "low_confidence_response",
    "interrupt_reason": "Model response failed compliance check for policy citation",
    "options": ["approve", "edit", "reject"]
  },
  "response_draft": "Dear Customer, We sincerely apologize...",
  "explanation": null,
  "updated_at": "2026-04-07T10:31:45Z"
}
```

**Errors:**
- `404 Not Found` - thread_id doesn't exist
- `410 Gone` - thread expired (after 24 hours)

---

#### 3. Submit Review Action

```http
POST /v1/complaints/{thread_id}/review
Content-Type: application/json

{
  "action": "approve",           // "approve" | "edit" | "reject"
  "edit_text": null              // Optional: edited response for "edit"
}
```

**Response (202 Accepted):**
```json
{
  "thread_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "Review action submitted. Pipeline resuming...",
  "updated_at": "2026-04-07T10:32:00Z"
}
```

**Errors:**
- `400 Bad Request` - Invalid action or edit_text
- `404 Not Found` - thread_id doesn't exist
- `409 Conflict` - Thread not in interrupt state

---

#### 4. Get Audit Events

```http
GET /v1/complaints/{thread_id}/audit
```

**Response (200 OK):**
```json
{
  "thread_id": "550e8400-e29b-41d4-a716-446655440000",
  "events": [
    {
      "timestamp": "2026-04-07T10:30:15Z",
      "sequence": 1,
      "node": "intake",
      "operation": "start",
      "model": "local-presidio",
      "latency_ms": 0,
      "tokens_used": 0,
      "decision": "complaint_scrubbed"
    },
    {
      "timestamp": "2026-04-07T10:30:18Z",
      "sequence": 2,
      "node": "classifier",
      "operation": "invoke",
      "model": "llama-3.3-70b-versatile",
      "latency_ms": 1247,
      "tokens_used": 312,
      "decision": "product: credit_card, issue: billing_error, confidence: 0.92"
    },
    {
      "timestamp": "2026-04-07T10:30:38Z",
      "sequence": 3,
      "node": "root_cause",
      "operation": "retrieve",
      "model": "llama-3.3-70b-versatile",
      "latency_ms": 2103,
      "tokens_used": 847,
      "decision": "No FRA matched"
    }
  ],
  "total_events": 24
}
```

---

#### 5. Get Daily Budget Status

```http
GET /v1/budget
```

**Response (200 OK):**
```json
{
  "daily_limit": 1000000,
  "used_today": 347821,
  "remaining": 652179,
  "percent_used": 34.78,
  "warning_threshold": 0.80,
  "degradation_threshold": 0.95,
  "status": "normal",
  "reset_at": "2026-04-08T00:00:00Z"
}
```

---

#### 6. Get Golden Demos (Optional)

```http
GET /v1/demos
```

**Response (200 OK):**
```json
{
  "demos": [
    {
      "demo_id": "demo_001_billing_dispute",
      "title": "Billing Error on Credit Card",
      "summary": "Customer was charged twice for same purchase",
      "category": "billing_error",
      "complaint_text": "I made a purchase on April 5th for $150..."
    },
    {
      "demo_id": "demo_002_unauthorized_transaction",
      "title": "Unauthorized Transaction",
      "summary": "Customer reports fraudulent charges they did not authorize",
      "category": "fraud",
      "complaint_text": "I noticed charges on my account..."
    }
  ]
}
```

---

### WebSocket Specification

#### Connection

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/complaints/550e8400-...');

ws.onopen = () => {
  console.log('Connected to pipeline stream');
};

ws.onmessage = (event) => {
  const update = JSON.parse(event.data);
  console.log('Stage update:', update.current_stage);
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};
```

#### Message Format

```json
{
  "type": "stage_update",
  "thread_id": "550e8400-e29b-41d4-a716-446655440000",
  "current_stage": "auditor_loop",
  "status": "pending",
  "stages": {},
  "timestamp": "2026-04-07T10:31:30Z"
}
```

#### Events

| Event | When | Payload |
|-------|------|---------|
| `stage_update` | Stage transitions or completes | Current snapshot |
| `interrupt` | Human review needed | Review state + options |
| `complete` | Pipeline finishes | Final snapshot + explanation |
| `error` | Unrecoverable error | Error message + stack |

---

## Frontend Pages & Components

### 1. Complaint Page (`/complaint`)

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  FinComplaint Review System     TOKEN BUDGET: 34.78% ▼      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────┐    ┌──────────────────────────────┐   │
│  │ Golden Demos     │    │ Complaint Composer           │   │
│  │                  │    │                              │   │
│  │ [Demo 1 Card]    │    │ ┌──────────────────────────┐ │   │
│  │ [Demo 2 Card]    │    │ │ [Complaint text box]     │ │   │
│  │ [Demo 3 Card]    │    │ │                          │ │   │
│  │ [Demo 4 Card]    │    │ │ [Submit] [Clear]         │ │   │
│  │ [Demo 5 Card]    │    │ └──────────────────────────┘ │   │
│  │                  │    │                              │   │
│  └──────────────────┘    └──────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Pipeline Visualization (after submission)             │   │
│  │                                                       │   │
│  │  [Intake] → [Classify] → [Root Cause] → [Remedy]    │   │
│  │     ✓            ✓           ✓          ⧖           │   │
│  │   0ms          1247ms       2103ms                   │   │
│  │  0 tokens      312 tokens   847 tokens              │   │
│  │                                                       │   │
│  │  [Writer] → [Auditor] → [Explainer]                 │   │
│  │     ✓           ⚠  Interrupt!      ⧳                │   │
│  │   2041ms         1893ms                             │   │
│  │   634 tokens     521 tokens                         │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ HUMAN REVIEW REQUIRED                                │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │                                                       │   │
│  │ Reason: Low confidence response audit              │   │
│  │ Current Output:                                      │   │
│  │ "We sincerely apologize for your experience..."     │   │
│  │                                                       │   │
│  │ [Approve] [Edit] [Reject]                            │   │
│  │                                                       │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 2. Audit Tab (`/audit/{thread_id}`)

```
Time              Node        Model              Decision            Tokens
─────────────────────────────────────────────────────────────────────────
10:30:15          intake      presidio           complaint_scrubbed  0
10:30:18          classifier  llama-3.3-70b     product: credit_card  312
10:30:38          root_cause  llama-3.3-70b     No FRA matched        847
10:31:05          remediator  llama-3.3-70b     MCP: SLA found        521
10:31:18          writer      llama-3.3-70b     Draft generated       634
10:31:45          auditor     llama-3.1-8b      ⚠ FAILED AUDIT        89
```

### 3. Components

#### ComplaintForm
- Textarea for manual input
- Golden demo card selector (click to load into form)
- Submit button (disabled until text > 10 chars)
- Clear button

#### PipelineView
- Horizontal/vertical stage timeline
- Expandable stage cards showing:
  - ✓/⧖/✗ status indicator
  - Model name
  - Latency (ms)
  - Tokens consumed
  - Expandable details (full output, evidence, etc.)

#### ReviewPanel
- Sticky footer that appears on interrupt
- Shows current stage output
- Three action buttons (approve/edit/reject)
- Edit button opens inline textarea

#### AuditTable
- Paginated 10-event-per-page scroll
- Columns: timestamp, node, model, decision, tokens, latency
- Click row to expand and see full JSON event

#### BudgetWidget
- Top-right header
- Shows: `Used: 347K / 1M (34.78%)`
- Color changes:
  - Green < 80%
  - Yellow 80-95%
  - Red > 95%

---

## Implementation Phases

### Phase A: Backend API & Library Refactoring
**Timeline:** 1 week

1. **A.1** - Refactor fincomplaint-ai to be library-importable
   - Create `src/__init__.py` public API
   - Create `src/api.py` with `ComplaintOrchestrator`
   - Update `pyproject.toml` with optional API dependencies
   - Write `.planning/API_CONTRACT.md` documentation

2. **A.2** - FastAPI backend shell
   - Setup FastAPI app (`backend/main.py`)
   - Implement REST route handlers (`backend/api/routes.py`)
   - Create Pydantic schemas (`backend/api/schemas.py`)
   - Add basic middleware (CORS, logging, error handling)

3. **A.3** - WebSocket integration
   - Implement WebSocket handler (`backend/api/websocket.py`)
   - Wire up live pipeline updates
   - Add connection lifecycle management

4. **A.4** - Thread persistence
   - In-memory thread storage (MVP)
   - SQLite snapshot persistence
   - Basic thread cleanup (24-hour TTL)

5. **A.5** - Backend tests
   - Unit tests for orchestrator
   - Route integration tests
   - WebSocket mock tests

### Phase B: Frontend UI Implementation  
**Timeline:** 1.5 weeks

1. **B.1** - Project setup
   - Initialize Next.js project
   - Configure TypeScript, ESLint, Prettier
   - Setup testing (Jest + React Testing Library)

2. **B.2** - Core components
   - ComplaintForm component
   - PipelineView component
   - ReviewPanel component

3. **B.3** - Pages & layout
   - Complaint page (`/complaint`)
   - Audit page (`/audit`)
   - Root layout with header/footer

4. **B.4** - API integration
   - Implement `useComplaint` hook
   - Implement `useWebSocket` hook
   - Create `api-client.ts` HTTP + WS wrapper

5. **B.5** - UI Polish
   - Design tokens (colors, spacing, typography)
   - Responsive mobile layout
   - Accessibility (ARIA labels, keyboard nav)

6. **B.6** - Frontend tests
   - Component unit tests
   - Page integration tests
   - E2E tests with Playwright

### Phase C: Local Development & Deployment
**Timeline:** 1 week

1. **C.1** - Docker containerization
   - Dockerfile for backend
   - Dockerfile for frontend
   - Docker Compose for local dev stack

2. **C.2** - Local development setup
   - Development scripts (setup, run, test, lint)
   - Hot reload configuration
   - Database seeding scripts

3. **C.3** - Documentation
   - DEVELOPMENT.md (local setup)
   - API.md (endpoint reference)
   - ARCHITECTURE.md (system design)
   - DEPLOYMENT.md (production checklist)

4. **C.4** - Production readiness
   - Kubernetes manifests (deployment, service, configmap)
   - Environment variable strategy
   - Redis integration for distributed threads
   - Nginx reverse proxy config

5. **C.5** - CI/CD pipeline
   - GitHub Actions workflows
   - Automated tests on PR
   - Docker image builds and registry push
   - Deployment automation

### Phase D: Testing & Hardening
**Timeline:** 1 week

1. **D.1** - End-to-end testing
   - Full complaint → review → complete flows
   - Multiple concurrent threads
   - Error recovery paths

2. **D.2** - Performance testing
   - Load testing (100+ concurrent complaints)
   - WebSocket connection stability
   - Memory profiling

3. **D.3** - Security hardening
   - Rate limiting per IP
   - CORS policy refinement
   - Input validation & sanitization
   - Dependency vulnerability scanning

4. **D.4** - Deployment testing
   - Local Docker Compose validation
   - Staging environment verification
   - Backup/restore procedures

---

## Technology Stack

### Backend
| Layer | Technology | Version | Rationale |
|-------|-----------|---------|-----------|
| Runtime | Python | 3.11+ | Core team expertise |
| Framework | FastAPI | 0.104+ | Async support, WebSocket, auto docs |
| ASGI Server | Uvicorn | 0.24+ | FastAPI recommended |
| Validation | Pydantic | 2.8+ | Type safety, auto JSON schema |
| Testing | pytest | 8.2+ | Existing fincomplaint-ai setup |
| Thread Store | Redis | 5.0+ | Session persistence (prod) |
| Logging | Python logging | stdlib | Simple, extensible |

### Frontend
| Layer | Technology | Version | Rationale |
|-------|-----------|---------|-----------|
| Library | React | 18+ | Modern component model |
| Framework | Next.js | 14+ | SSR, API routes, deployment |
| Language | TypeScript | 5.0+ | Type safety, IDE support |
| Styling | Tailwind CSS | 3+ | Utility-first, responsive |
| HTTP Client | axios / fetch | - | REST API calls |
| WS Client | native WebSocket | - | Browser built-in |
| Testing | Jest + RTL | - | Standard React testing |
| E2E Testing | Playwright | - | Modern cross-browser |

### Infrastructure
| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Containerization | Docker | Standard industry practice |
| Orchestration (dev) | Docker Compose | Simple local development |
| Orchestration (prod) | Kubernetes | Scalability, self-healing |
| Reverse Proxy | Nginx | Efficient load balancing |
| Database | PostgreSQL | Production persistence |
| Cache | Redis | Session store, rate limiting |
| Monitoring | Prometheus + Grafana | Observable metrics |
| Logging | ELK stack | Centralized log aggregation |

---

## Deployment Targets

### Development (Local)
```bash
docker-compose up
# Backend: http://localhost:8000
# Frontend: http://localhost:3000
# Docs: http://localhost:8000/docs
```

### Staging (Cloud)
- AWS ECS or Kubernetes
- RDS Postgres + ElastiCache Redis
- Application Load Balancer
- CloudWatch monitoring

### Production
- Kubernetes cluster (EKS/GKE/AKS)
- Managed Postgres (RDS/Cloud SQL)
- Managed Redis (ElastiCache/Memory Store)
- CDN for frontend assets
- OpenTelemetry for distributed tracing

---

## Acceptance Criteria

### MVP (v1.0)
- [ ] fincomplaint-ai library is importable and documented
- [ ] Backend REST API passes all route tests
- [ ] WebSocket streaming works reliably
- [ ] Frontend pages render without errors
- [ ] Golden demo flow works end-to-end
- [ ] Review actions (approve/edit/reject) work
- [ ] Audit tab displays events chronologically
- [ ] Budget widget updates live
- [ ] Local Docker Compose setup works out-of-box
- [ ] Documentation is complete and accurate

### v1.1 (Polish)
- [ ] Frontend responsive on mobile
- [ ] Load testing passes (100+ concurrent users)
- [ ] Security audit completed
- [ ] Kubernetes manifests tested in staging
- [ ] Prometheus metrics exposed and grafana dashboard working
- [ ] Backup/restore procedures documented and tested

### v2.0 (Future)
- [ ] Multi-tenant auth (API keys / OAuth2)
- [ ] Distributed thread storage (Redis)
- [ ] Advanced fairness metrics dashboard
- [ ] Mobile app (React Native / Flutter)
- [ ] Batch complaint processing
- [ ] Advanced observability (custom dashboards, alerting)

---

## Environment Variables

### Backend

```bash
# LLM Configuration
GROQ_API_KEY=gsk_xxxxxxxxxxxxx
GROQ_BASE_URL=https://api.groq.com/openai/v1
GROQ_TIMEOUT_SECONDS=60
GROQ_MAX_RETRIES=3

# Complaint Threading
THREAD_PERSIST_DIR=./.complaint_threads
THREAD_TTL_HOURS=24
STATUS_POLL_INTERVAL_MS=500

# Redis (production only)
REDIS_URL=redis://localhost:6379/0

# Postgres (production only)
DATABASE_URL=postgresql://user:pass@localhost/complaints

# CORS
ALLOWED_ORIGINS=http://localhost:3000,https://app.example.com

# Rate Limiting
RATE_LIMIT_PER_IP=100/hour
```

### Frontend

```bash
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_WS_URL=ws://localhost:8000

# Environment
NEXT_PUBLIC_ENV=development
NEXT_PUBLIC_VERSION=0.1.0
```

---

## Future Enhancements (Out of Scope for MVP)

1. **Advanced Observability**
   - OpenTelemetry integration
   - Custom Grafana dashboards
   - Alert rules (latency, error rates)
   - Distributed tracing across service boundaries

2. **Advanced Auth**
   - OAuth2 / OIDC support
   - Multi-tenant request routing
   - RBAC for operators/admins
   - Audit access controls

3. **Streaming & Async**
   - Server-sent events (SSE) alternative to WebSocket
   - Message queue for async complaint processing
   - Batch export (CSV, PDF)

4. **Analytics**
   - Fairness dashboard (disparate impact by demographics)
   - Performance metrics (classification accuracy, resolution time)
   - Complaint category trends
   - Model performance comparison

5. **Mobile Apps**
   - React Native mobile app
   - Flutter cross-platform variant
   - Offline mode with sync

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **API Response Time** | < 100ms (p99) | Prometheus latency histogram |
| **WebSocket Latency** | < 50ms updates | Client-side performance monitoring |
| **Uptime** | 99.9% | Kubernetes health checks |
| **Error Rate** | < 0.1% | Application error tracking |
| **Complaint Throughput** | 1000+ concurrent | Load test results |
| **Frontend Lighthouse Score** | 80+ | Automated audits |
| **Test Coverage** | 80%+ | Code coverage reports |
| **Documentation Completeness** | 100% | Checklist verification |

---

**Document Version:** 1.0  
**Last Updated:** April 7, 2026  
**Owner:** AI Backend Team  
**Status:** Planning Ready for Implementation

For clarifications or updates, see the `.planning/` directory or contact the backend team lead.
