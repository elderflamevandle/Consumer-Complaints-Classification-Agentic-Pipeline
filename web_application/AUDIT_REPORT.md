# FinComplaint AI — Web Application Audit Report

> **Date:** 2026-04-09
> **Scope:** `web_application/` — full backend + frontend review (every file)
> **Auditor:** Claude (automated deep audit)

---

## Table of Contents

1. [What Is Already Implemented](#1-what-is-already-implemented)
2. [What Is Partially Implemented](#2-what-is-partially-implemented)
3. [What Is Completely Missing](#3-what-is-completely-missing)
4. [Bugs & Security Issues Found](#4-bugs--security-issues-found)
5. [Priority Implementation Plan](#5-priority-implementation-plan)
6. [Feature Additions to Consider](#6-feature-additions-to-consider)

---

## 1. What Is Already Implemented

### Infrastructure

| Item | Status |
|------|--------|
| Three-service Docker Compose (Redis + FastAPI + Next.js) | ✅ Complete |
| Health-check chain (Redis → backend → frontend) | ✅ Complete |
| Multi-stage Dockerfiles (non-root users) | ✅ Complete |
| Next.js standalone output (`.next/standalone` copy pattern) | ✅ Complete |
| MongoDB Atlas async Motor connection with lifespan hooks | ✅ Complete |

### Auth System

- **JWT HS256 / RS256 dual-mode** — auto-switches to RS256 when PEM keys are configured
- **Refresh token rotation** — opaque UUID4 tokens, SHA-256 hashed in DB, TTL index auto-purges from MongoDB, revoked in Redis on rotation
- **Bcrypt password hashing** at 12 rounds; constant-time verification; timing-attack dummy hash on login for non-existent users
- **IP-based brute-force counter** in Redis with per-user account lockout
- **Password policy validation** — regex enforcing uppercase + lowercase + digit + special char + 8-char minimum, mirrored identically on frontend zod schema
- **Token stored in-memory only** on frontend — no localStorage; correct XSS mitigation; `_refreshPromise` deduplication prevents race conditions on concurrent 401 retries
- **Refresh cookie scoped** to `/api/auth/refresh` path, httpOnly

### RBAC

- **Three roles**: `admin`, `analyst`, `viewer` — enforced via FastAPI dependency factories (`AdminUser`, `AnalystUser`, `CurrentUser`)
- **Data scoping in list queries** — analysts see only their own complaints; admins see all
- **Role-based frontend UI** — analyst/admin get internal analysis toggle; viewers never see it
- **Admin panel** with user list, role change, activate/deactivate; self-modification prevention (cannot demote own account or deactivate self)

### Mock Pipeline (8-node, fully wired end-to-end)

```
intake → classifier → routing → root_cause → remediator → writer → auditor → explainer
```

- **PII scrubbing** in intake: SSN, 16-digit credit card, formatted card, email, phone patterns
- **Human-in-the-loop interrupt** — routing node pauses pipeline at `INTERRUPTED` status awaiting approve/edit/reject
- **asyncio.Queue WebSocket streaming** — real-time updates pushed to browser as each node completes
- **Pipeline stage persistence** — each node's output, `latency_ms`, `tokens_used` saved to MongoDB `pipeline_stages` collection
- **ReviewPanel** wired correctly — approve/edit/reject actions call `POST /api/complaints/{id}/review`

### Security Middleware Stack

| Middleware | Function |
|-----------|----------|
| `SanitizeMiddleware` | bleach HTML stripping on JSON bodies; HTTP parameter pollution guard |
| `CSRFMiddleware` | Double-submit cookie, `hmac.compare_digest` constant-time comparison |
| `CORSMiddleware` | Configurable allowed origins from settings |
| `SecurityHeadersMiddleware` | HSTS, X-Frame-Options, X-Content-Type-Options, CSP, Referrer-Policy, Permissions-Policy, server header removal |

### Audit Log

- **Append-only audit log** in MongoDB — all auth events, complaint submissions, pipeline stage transitions, review decisions
- Comprehensive `AuditAction` StrEnum covering the full lifecycle
- Complaint-level trail at `GET /api/complaints/{id}/audit`; system-wide at `GET /api/admin/audit`

### Frontend Pages

| Page | Route | Status |
|------|-------|--------|
| Landing page | `/` | ✅ Static, no auth dependency |
| Login form | `/login` | ✅ react-hook-form + zod |
| Register form | `/register` | ✅ Password policy mirrored |
| Dashboard | `/dashboard` | ✅ Stats + charts + recent list |
| Complaints list | `/complaints` | ✅ Paginated, status filter tabs |
| New complaint | `/complaints/new` | ✅ Char counter, state dropdown, demo presets |
| Complaint detail | `/complaints/[id]` | ✅ Role-split customer vs internal view |
| Admin panel | `/admin` | ✅ Users + system audit log tabs |
| Legacy redirects | `/complaint`, `/audit` | ✅ Server-side redirect |

### Frontend Infrastructure

- **Axios client** — auth header injection, CSRF injection, 401→refresh→retry, DOMPurify recursive sanitization
- **Zustand stores** — auth store + complaints store with WebSocket update handler
- **Custom hooks** — `useComplaintWS` (WebSocket), `useComplaintDetail` (REST + WS combined)
- **Design token system** — CSS variables (HSL channel), light + dark mode, Tailwind integration
- **Reusable components** — `Badge` (7 variants), `PipelineView`, `ReviewPanel`, `AuditTable`, `Navbar`

---

## 2. What Is Partially Implemented

### Pipeline Integration

- `backend/core/orchestrator.py` is architecturally correct (thread-safe wrapper, async submit/status/resume) but **imports `fincomplaint_ai` which doesn't exist**. It is the bridge to the real `src/` pipeline but can never run.
- `complaint_service.py` comment says `resume_pipeline_after_review` "skips intake + classifier + routing" — **the mock pipeline always re-runs all 8 nodes**. Partial resume is designed but not implemented.

### Budget / Token Tracking

- `BudgetService` class scaffolded with `get_budget_status()`, `record_usage()`, `daily_limit`
- **`used_today = 347821` is hardcoded mock data** — no real token counting
- `config.py` has `daily_token_budget = 200_000` but `BudgetService.daily_limit = 1_000_000` — inconsistent; config value is never read
- Service is instantiated in `api/routes.py` (dead code) — never reachable

### Rate Limiting

- `slowapi` is configured globally at 100 requests / 15 minutes
- `services/rate_limiter.py` is a custom in-memory limiter — never used, superseded by slowapi but not deleted
- Admin endpoints have **no per-endpoint `@limiter.limit()` decorators**

### WebSocket Authentication

- WS endpoint at `/api/complaints/ws/{id}` accepts connections with **no auth check**
- All REST complaint endpoints are auth-gated but the WS path was never wired to a dependency

### CSRF WebSocket Exemption

- `csrf.py` exempts `request.url.path.startswith("/ws")`
- Real WS path is `/api/complaints/ws/{id}` — **the exemption never fires**
- WebSocket upgrade requests hit CSRF validation and are rejected

### Dashboard Stats Accuracy

- Admin stat tiles and Recharts charts render correctly
- `GET /api/admin/audit` returns `total: len(events)` (page size), **not** the true collection count — pagination metadata is wrong
- `last_30d` variable is computed in `dashboard_stats` but never used in any query — 30-day trend data missing

### ReviewPanel Edit Flow

- Edit action card renders and textarea is displayed
- **`editedText` initial value is `''`**, not `complaint.scrubbed_text`
- If reviewer submits without typing, backend rejects with 422 (`min_length=20`) but frontend has no client-side validation guard

### Toast / Notification System

- `@radix-ui/react-toast` installed in `package.json`
- **No `<ToastProvider>` mounted anywhere** — package is completely unused
- Errors shown as inline text banners; no success toasts exist

---

## 3. What Is Completely Missing

### Real AI Pipeline Integration

- `src/` has not been packaged as `fincomplaint_ai` Python library — no `pyproject.toml`, no `setup.py`, no `pip install -e` in requirements
- No import path, no volume mount of `src/` in docker-compose for dev
- The web app runs **zero real AI/Groq/ChromaDB calls** — 100% mock data

### Tests

- **Zero test files exist** anywhere in `web_application/`
- No `conftest.py`, no fixtures, no mock factories
- `pytest` and `pytest-asyncio` are installed but there is nothing to run

### `.dockerignore`

- No `.dockerignore` in `web_application/`
- Docker build context includes `.env` (real credentials), `__pycache__`, `node_modules`, `.next`
- Real secrets may be embedded in image layers

### Dark Mode Toggle

- CSS variables for `.dark` class are fully defined
- `tailwind.config.js` sets `darkMode: ['class']`
- **No toggle button exists anywhere** in the UI — dark mode is unreachable by users

### Mobile Navigation

- `Navbar` hides all nav links below `sm` breakpoint
- **No hamburger menu / slide-out drawer** — mobile users see only the brand logo and logout button

### SLA Timer Display

- `policy_citations.sla_window` is stored in the complaint document
- **Never rendered on the complaint detail page** — the field is accessed with `as any` cast but not displayed

### Seed Script

- Admin user was created via a one-off `docker exec` + Python script during initial setup
- **No `scripts/seed_admin.py`** — reproducing the setup requires manual steps
- No documented `make seed` equivalent

### DataTable Component

- Complaints list is a plain `<div>` loop with no sortable/filterable columns
- Admin users list is a plain `<table>` with no sorting or filtering
- `DataTable` was listed in the original Phase 5 spec but was not implemented

### Notifications / Webhooks

- No email notifications on complaint status changes
- No webhook dispatch to external systems
- No SLA breach alerts

### CFPB RAG Integration

- `cfpb_col()` defined in `mongodb.py` but never called
- Mock pipeline generates fake CFPB case IDs and random citation dates
- ChromaDB is not referenced anywhere in the web application layer

---

## 4. Bugs & Security Issues Found

### 🔴 Critical

#### SEC-1 — Real MongoDB credentials hardcoded in source
**File:** `backend/config.py` lines 31–32 and `backend/.env`

`mongodb+srv://knimbalk_db_user:Xw8rLGNq2aqpk46C@umd.mcnucik.mongodb.net` is the default value in `config.py`. Anyone with repo read access owns the production database.

**Fix:**
```python
# config.py
MONGODB_URL: str = Field(..., description="MongoDB Atlas connection string")
```
Rotate credentials immediately. Confirm `.env` is truly git-ignored:
```bash
git log --all --full-history -- backend/.env
git rm --cached backend/.env  # if it appears in history
```

---

#### SEC-2 — Real JWT secret committed
**File:** `backend/.env`

`JWT_SECRET_KEY=a08562053ca446fc8948b97e9b37df07...` is committed. All tokens signed with this key are compromised.

**Fix:** Rotate the secret, regenerate all active sessions.

---

#### SEC-3 — Unauthenticated WebSocket endpoint
**File:** `backend/routers/complaints.py` line 214

`/api/complaints/ws/{complaint_id}` accepts connections with no auth check. Any client knowing a UUID can stream real-time pipeline output.

**Fix:**
```python
@router.websocket("/ws/{complaint_id}")
async def pipeline_ws(
    websocket: WebSocket,
    complaint_id: str,
    token: str = Query(...),           # pass access token as ?token=
    db=Depends(get_db),
):
    payload = decode_access_token(token)
    # validate user + ownership before accepting
    await websocket.accept()
```

---

#### SEC-4 — CSRF WebSocket path exemption is broken
**File:** `backend/middleware/csrf.py`

Exemption checks `request.url.path.startswith("/ws")`. Actual WS path is `/api/complaints/ws/{id}`. Exemption never fires — all WebSocket upgrade requests are blocked by CSRF.

**Fix:**
```python
# Replace:
if request.url.path.startswith("/ws"):
# With:
if "/ws/" in request.url.path or request.url.path.startswith("/ws"):
```

---

### 🟠 High

#### BUG-1 — Docker networking: `NEXT_PUBLIC_API_URL=http://backend:8000` not browser-reachable
**File:** `docker-compose.yml` frontend environment

`backend` is a Docker-internal hostname. Browsers on the host machine cannot resolve it. All client-side Axios calls fail.

**Fix:**
```yaml
# docker-compose.yml — frontend environment
- NEXT_PUBLIC_API_URL=http://localhost:8000    # for local dev
```
Document that production deployments must set this to the public hostname.

---

#### BUG-2 — Redis unavailability causes hard 500 on login
**File:** `backend/auth/router.py` line 189

`get_redis()` raises `RuntimeError` if Redis is not initialized. The login endpoint calls `get_login_attempts(ip)` with no try/except guard. If Redis is down (which `main.py` silently allows), the first login attempt throws HTTP 500.

**Fix:**
```python
try:
    attempts = await get_login_attempts(ip)
except RuntimeError:
    attempts = 0  # Redis unavailable — skip lockout check, log warning
```

---

#### SEC-5 — `--forwarded-allow-ips=*` allows IP spoofing
**File:** `Dockerfile.backend`

Any client can inject `X-Forwarded-For: 1.2.3.4` to bypass rate limiting and account lockout (both key on `request.client.host`).

**Fix:** Scope to the reverse proxy IP (Docker gateway or specific load balancer IP).

---

#### BUG-3 — Dead code with broken import
**Files:** `api/routes.py`, `api/websocket.py`, `core/orchestrator.py`

All three import `fincomplaint_ai` which doesn't exist. They are never mounted so the app runs — but accidentally mounting any of them causes immediate `ModuleNotFoundError`.

**Fix:** Delete all three files, or add an `ImportError` guard:
```python
try:
    from fincomplaint_ai import ComplaintOrchestrator as FinComplaintOrchestrator
except ImportError:
    FinComplaintOrchestrator = None
```

---

#### BUG-4 — `resume_pipeline_after_review` re-runs all 8 nodes
**File:** `backend/services/complaint_service.py` line 324

The comment says it "skips intake + classifier + routing" but `MockPipelineRunner.run()` always starts from `intake`, overwriting all classification outputs.

**Fix:** Add a `start_from` parameter to `MockPipelineRunner`:
```python
async def run(self, start_from: str = "intake") -> AsyncGenerator[PipelineUpdate, None]:
    skip = True
    for node in PIPELINE_NODES:
        if node == start_from:
            skip = False
        if skip:
            continue
        # ... run node
```

---

### 🟡 Medium

#### BUG-5 — `datetime.utcnow()` deprecated and inconsistent
**Files:** `auth/router.py`, `models/user.py`, `models/complaint.py`, `models/audit_log.py`, `models/refresh_token.py`, `routers/admin.py`

Returns naive datetime. Mixed with `datetime.now(tz=timezone.utc)` in the same files. Deprecated in Python 3.12.

**Fix (global replace):**
```python
# Remove:
from datetime import datetime
datetime.utcnow()

# Replace with:
from datetime import datetime, timezone
datetime.now(tz=timezone.utc)
```

---

#### BUG-6 — 422 validation errors not surfaced to user
**Files:** `frontend/app/(auth)/register/page.tsx`, `frontend/app/complaints/new/page.tsx`, `frontend/components/complaints/ReviewPanel.tsx`

Backend returns 422 with `detail` as an array of Pydantic error objects. Frontend reads `e.response?.data?.detail` as a string — gets `undefined` — shows generic fallback message.

**Fix in `lib/api-client.ts`:**
```typescript
const detail = e.response?.data?.detail
const message = Array.isArray(detail)
  ? detail[0]?.msg ?? 'Validation error'
  : detail ?? 'An error occurred'
```

---

#### BUG-7 — Audit log `total` count is wrong
**File:** `backend/routers/admin.py`

`GET /api/admin/audit` returns `total: len(events)` (the current page size), not the MongoDB collection count. Pagination shows "100 of 100" even when there are 10,000 records.

**Fix:**
```python
total = await audit_logs_col().count_documents({})
```

---

#### BUG-8 — `ReviewPanel` submits empty `editedText`
**File:** `frontend/components/complaints/ReviewPanel.tsx` line 16

Edit action initial value is `editedText = ''`. Submitting without typing sends `edited_text: ""`, which backend rejects with 422. No client-side guard.

**Fix:**
```typescript
const [editedText, setEditedText] = useState(complaint.scrubbed_text ?? '')
// Before submission:
if (action === 'edit' && editedText.trim().length < 20) {
  setError('Edited text must be at least 20 characters')
  return
}
```

---

#### BUG-9 — No `.dockerignore`
**Location:** `web_application/`

`.env`, `__pycache__`, `node_modules`, `.next` included in build context.

**Fix** — create `web_application/.dockerignore`:
```
**/.env
**/__pycache__
**/*.pyc
**/node_modules
**/.next
**/.git
```

---

#### BUG-10 — Admin actions have no confirmation or error handling
**File:** `frontend/app/admin/page.tsx`

Role change fires immediately on `<select>` change. Deactivate fires immediately on click. No try/catch — silent failures.

**Fix:** Add `window.confirm()` guards and wrap API calls in try/catch with error state display.

---

### 🟢 Low

| # | Issue | File |
|---|-------|------|
| L-1 | `httpx==0.27.0` appears twice | `requirements.txt` |
| L-2 | `set_csrf_token` / `get_csrf_token` are dead code (CSRF middleware doesn't use Redis) | `db/redis_client.py` |
| L-3 | `cfpb_col()` defined but never called | `db/mongodb.py` |
| L-4 | `last_30d` variable computed but never used | `routers/admin.py` |
| L-5 | `line-clamp-2`/`line-clamp-3` redefined — redundant with Tailwind 3.3+ built-in | `styles/globals.css` |
| L-6 | `Promise.all([singleCall])` — unnecessary wrapper | `app/dashboard/page.tsx` |
| L-7 | `Badge` renders as `<div>` — invalid inside `<p>` contexts | `components/ui/badge.tsx` |
| L-8 | `NavLink` has no active state highlight | `components/layout/Navbar.tsx` |
| L-9 | `useEffect(() => { return clearError }, [])` — clears on unmount, not mount | `app/(auth)/login/page.tsx` |
| L-10 | Dark mode tokens defined but no toggle to activate them | `tailwind.config.js` |
| L-11 | `AuditTable` silently swallows fetch errors | `components/complaints/AuditTable.tsx` |
| L-12 | WebSocket `onerror` is completely silent — user sees stale data with no indication | `hooks/useComplaint.ts` |
| L-13 | No WebSocket reconnect / backoff logic | `hooks/useComplaint.ts` |
| L-14 | `complaintsApi.list` errors swallowed in dashboard load | `app/dashboard/page.tsx` |

---

## 5. Priority Implementation Plan

### Sprint 1 — Security Hardening *(before any public deployment)*

- [ ] **Rotate all secrets** — new MongoDB password, JWT secret, CSRF secret
- [ ] **Remove default MongoDB URL from `config.py`** — change to `Field(...)` with no default
- [ ] **Confirm `.env` not in git history** — `git log --all --full-history -- backend/.env`; run `git rm --cached` if needed
- [ ] **Fix CSRF WebSocket exemption** — `"/ws/" in request.url.path` instead of `startswith("/ws")`
- [ ] **Add WebSocket authentication** — query-param access token, validate in WS handler
- [ ] **Fix Docker networking** — `NEXT_PUBLIC_API_URL=http://localhost:8000` for local dev
- [ ] **Add `.dockerignore`** — prevent secrets from embedding in image layers
- [ ] **Remove `--forwarded-allow-ips=*`** — scope to gateway IP

### Sprint 2 — Bug Fixes

- [ ] **Fix `datetime.utcnow()`** — global replace across 7 backend files (~15 occurrences)
- [ ] **Fix 422 error display** — update error handler in `api-client.ts` to extract `detail[0].msg`
- [ ] **Fix `ReviewPanel` `editedText`** — initialize to `complaint.scrubbed_text`, add min-length guard
- [ ] **Fix audit log `total`** — add `count_documents` query in `admin.py`
- [ ] **Fix `resume_pipeline_after_review`** — add `start_from` parameter to `MockPipelineRunner`
- [ ] **Add error handling + confirmation** to admin role-change and deactivate actions
- [ ] **Graceful Redis degradation** — try/except in `auth/router.py`; allow login if Redis is down
- [ ] **Delete dead code** — `api/routes.py`, `api/websocket.py`, `services/rate_limiter.py` stubs

### Sprint 3 — Real Pipeline Integration

- [ ] **Package `src/` as installable library** — add `src/pyproject.toml` with `name = "fincomplaint_ai"`
- [ ] **Wire `core/orchestrator.py`** — fix `settings.thread_persist_dir` reference; test import
- [ ] **Add feature flag** — `USE_MOCK_PIPELINE=true/false` in `config.py`; `complaint_service.py` switches between `MockPipelineRunner` and `FinComplaintOrchestrator`
- [ ] **Real token tracking** — replace `BudgetService` stub; accumulate from pipeline node `tokens_used` fields

### Sprint 4 — Completeness

- [ ] **Seed script** — `scripts/seed_admin.py` with argparse; document in README
- [ ] **Mount `<ToastProvider>`** in `app/layout.tsx`; replace inline error banners with toasts
- [ ] **SLA timer display** — render `policy_citations.sla_window` on complaint detail as a deadline badge
- [ ] **DataTable component** — sortable/filterable table for complaints list (sort by severity, date, status)
- [ ] **Fix admin audit pagination** — `count_documents` for `total`; add offset pagination on frontend

### Sprint 5 — Polish & Tests

- [ ] **Write tests** — pytest for auth router, complaint service, mock pipeline; RTL for forms and RBAC rendering
- [ ] **Mobile navigation** — hamburger menu + slide-out drawer for `< sm` breakpoint
- [ ] **Dark mode toggle** — button in Navbar, persist in `localStorage`
- [ ] **NavLink active state** — `usePathname()` highlight in Navbar
- [ ] **WebSocket reconnect backoff** — exponential backoff in `useComplaintWS`; "Live updates paused" toast on `onerror`
- [ ] **Error boundaries** — `app/error.tsx` global boundary; loading skeletons for data-fetching pages

---

## 6. Feature Additions to Consider

### 🔵 High Business Value

#### 1. Complaint Search & Filtering
The `complaints` collection already has a **full-text index** on `complaint_text`. Add `GET /api/complaints?q=<search>` and a search bar on the list page. Analysts can find complaints by keywords without browsing pages.

#### 2. SLA Dashboard Widget
Pipeline outputs `sla_window` and `severity`. Build an admin widget showing complaints **approaching or past SLA deadline** sorted by severity. CRITICAL/HIGH complaints unresolved within SLA generate regulatory risk.

#### 3. Exportable Compliance PDF Report
Add `GET /api/complaints/{id}/report.pdf` rendering the full pipeline output (classification, root cause, remediation, audit verdict, response letter) as a downloadable PDF using `weasyprint` or `reportlab`. The auditor `verdict: PASS / FAIL` becomes the compliance attestation document.

#### 4. Batch Complaint Import (CSV)
Add `POST /api/complaints/batch` accepting a CSV upload, queuing each row through the pipeline, returning a job ID for status polling. Useful for retrospective analysis of a complaint backlog.

#### 5. Real-Time Admin Dashboard
Replace static Recharts charts with a live-updating view via `/api/admin/ws/stats` WebSocket. Admins see live throughput as complaints are submitted and pipelines complete — no page refresh needed.

---

### 🟡 Medium Value

#### 6. Analyst Assignment & Ownership Transfer
`POST /api/complaints/{id}/assign` exists in the router but **has no UI**. Add an "Assign to Analyst" dropdown on the complaint detail page visible to admins, paired with email notification.

#### 7. Two-Factor Authentication (TOTP)
Add TOTP support using `pyotp`. On login, if MFA is enabled, issue a short-lived `mfa_pending` JWT that only grants access to `POST /api/auth/mfa/verify`. On successful verification, issue full access + refresh tokens.

#### 8. Complaint History / Versioning
When a reviewer edits complaint text in the human-review step, the original and edited versions are not preserved. Add a `versions` array to `ComplaintDocument` snapshotting text at each human intervention.

#### 9. Webhook Outbound Notifications
Allow admins to configure webhook URLs (`POST /api/admin/webhooks`) that receive a POST payload when a complaint reaches a specific status (e.g., `auditor FAIL` or any `CRITICAL` severity). Integrates with Slack, PagerDuty, or internal ticketing.

#### 10. Complaint Templates Library
The "New Complaint" page has 3 hardcoded demo presets. Build a `/complaints/templates` page where admins can create, edit, and delete named templates stored in a MongoDB `templates` collection.

---

### 🟢 Lower Priority

#### 11. Dark Mode Toggle
The entire design token system is already in place. A single `onClick` to toggle `document.documentElement.classList.toggle('dark')` with `localStorage` persistence is all that's needed.

#### 12. Keyboard Shortcut Layer
Power users reviewing dozens of complaints daily would benefit from shortcuts: `j/k` to navigate the list, `a` to approve, `r` to reject. Implement via a `useHotkeys` hook.

#### 13. Complaint Tagging
Free-form tags on complaints (`mortgage`, `Q4-2025`, `repeat-customer`) stored as an array in MongoDB. Filter by tag in list view. Useful for grouping complaints into audit cohorts.

#### 14. CFPB RAG Integration
`cfpb_col()` is already defined in `mongodb.py`. The frontend `NodeOutputPreview` for `root_cause` already renders `evidence` cards with `citation` fields. The display layer is **ready** — only the real ChromaDB data source needs to be wired in once the real pipeline is integrated.

---

*Generated by automated deep audit — all findings cross-referenced against actual source files.*
