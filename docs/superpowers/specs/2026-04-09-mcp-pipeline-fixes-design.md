# Design: MCP Server & Pipeline Agentic Flow Fixes

**Date:** 2026-04-09  
**Status:** Approved  
**Scope:** Fix 4 bugs in the MCP SLA integration and LangGraph pipeline

---

## Problem Summary

Four issues were found after the last refactor (HITL removal + prompt centralization):

| # | Issue | Severity |
|---|-------|----------|
| 1 | MCP issue-type key mismatch — regulations JSON uses short keys (`BILLING`, `FRAUD`) but classifiers now emit full CFPB display strings | CRITICAL |
| 2 | MCP server path is relative to CWD — breaks when run from any non-root directory | HIGH |
| 3 | Routing triage (confidence < 0.70, HIGH compliance risk, CRITICAL severity) was silently dropped with HITL removal | HIGH |
| 4 | Three pipeline files (`response_loop.py`, `routing.py`, `interrupts.py`) + `state.py` are orphaned dead code | MEDIUM |

---

## Architecture

No new nodes or edges are added to the LangGraph graph. All changes are contained to:
- Data: `mcp_server/mock_regulations.json`
- Tool: `src/tools/mcp_policy_client.py`
- State: `src/graph/langgraph_state.py`
- Node: `src/graph/nodes.py` (issue_classifier_node only)
- Cleanup: delete 3 files, trim 1 file

---

## Fix 1: Expand `mock_regulations.json`

The MCP server's `_normalize_issue()` converts display strings to `UPPER_SNAKE_CASE`.
For example, `"Fraud or scam"` → `"FRAUD_OR_SCAM"`.

The regulations file must be keyed on the normalized form. We group all 40 CFPB
issue types into 6 SLA buckets based on regulatory domain:

| Bucket Key (normalized) | CFPB Issue Types Covered | SLA | Regulatory Basis |
|-------------------------|--------------------------|-----|-----------------|
| `FRAUD_OR_SCAM`, `UNAUTHORIZED_TRANSACTIONS`, `FRAUD_ALERTS` | Fraud/unauthorized | 10 days | Electronic fund transfer fraud handling |
| `FEES_OR_INTEREST`, `PURCHASE_ON_STATEMENT`, `PROBLEM_WHEN_MAKING_PAYMENTS`, `LENDER_CHARGING_ACCOUNT`, `UNEXPECTED_FEES`, `WRONG_AMOUNT`, `FUNDS_LOW` | Billing disputes | 21 days | Regulation Z billing error framework |
| `INCORRECT_INFORMATION`, `IMPROPER_USE_OF_REPORT`, `INVESTIGATION_EXISTING_PROBLEM`, `INVESTIGATION_EXISTING_ISSUE`, `UNABLE_CREDIT_REPORT`, `CREDIT_MONITORING`, `IDENTITY_THEFT_PROTECTION` | Credit reporting | 30 days | FCRA dispute investigation requirements |
| `ATTEMPTS_TO_COLLECT_NOT_OWED`, `COMMUNICATION_TACTICS`, `FALSE_STATEMENTS`, `THREATENED_SHARE_INFO`, `NEGATIVE_OR_LEGAL_ACTION`, `WRITTEN_NOTIFICATION`, `ELECTRONIC_COMMUNICATIONS` | Debt collection | 30 days | FDCPA consumer protection standards |
| `STRUGGLING_TO_PAY_MORTGAGE`, `APPLYING_FOR_MORTGAGE`, `CLOSING_ON_MORTGAGE`, `TROUBLE_DURING_PAYMENT`, `STRUGGLING_TO_PAY_LOAN`, `STRUGGLING_TO_PAY_BILL` | Hardship/loss mit | 30 days | CFPB loss mitigation and hardship guidelines |
| All others (`CLOSING_AN_ACCOUNT`, `MANAGING_AN_ACCOUNT`, etc.) | General account | 30 days | CFPB complaint response baseline guidance |

State overrides (`CA` for billing, `NY` for fraud) are preserved from existing data.

Each entry follows the existing schema:
```json
"FRAUD_OR_SCAM": {
  "default": { "sla_window": "...", "required_actions": [...], "regulatory_basis": "..." },
  "states": { "NY": { ... } }
}
```

---

## Fix 2: Absolute MCP Server Path

**File:** `src/tools/mcp_policy_client.py`

**Before:**
```python
DEFAULT_SERVER_PATH = Path('mcp_server/server.py')
```

**After:**
```python
DEFAULT_SERVER_PATH = Path(__file__).parent.parent.parent / 'mcp_server' / 'server.py'
```

This anchors the path to the file's own location, making it CWD-independent.

---

## Fix 3: Triage Flag in State

**File:** `src/graph/langgraph_state.py`

Add two optional fields to `PipelineState`:

```python
triage_flag: bool          # True when HIGH compliance risk or CRITICAL severity
triage_reason: str         # e.g. "high_compliance_risk,critical_severity"
```

**File:** `src/graph/nodes.py` — `issue_classifier_node`

After the issue classifier runs, compute and include in the return dict:
```python
triage_flag = (
    issue_result.compliance_risk == ComplianceRisk.HIGH
    or issue_result.severity == SeverityLevel.CRITICAL
    or issue_result.confidence < 0.70
)
reasons = []
if issue_result.confidence < 0.70:
    reasons.append("low_confidence")
if issue_result.compliance_risk == ComplianceRisk.HIGH:
    reasons.append("high_compliance_risk")
if issue_result.severity == SeverityLevel.CRITICAL:
    reasons.append("critical_severity")
triage_reason = ",".join(reasons) if reasons else ""
```

The flag is visible in the final `PipelineState` returned by `run_complaint()`. No graph
edges change — all complaints still flow through identically, but callers can inspect
`state["triage_flag"]` to decide on post-processing escalation.

---

## Fix 4: Delete Orphaned Files

These files are not called from the LangGraph pipeline and exist only from the
pre-HITL-removal era:

| File | Why safe to delete |
|------|--------------------|
| `src/graph/response_loop.py` | Not imported by any live pipeline file |
| `src/graph/routing.py` | Not imported by any live pipeline file |
| `src/graph/interrupts.py` | Not imported by any live pipeline file |
| `src/graph/state.py` | All exports consumed only by the 3 files above |

`ui/review.py` and `ui/dashboard_state.py` reference `ReviewPanelState` and
`ReviewInterruptPayload` only via `TYPE_CHECKING` guards and docstring comments —
no runtime breakage from deleting `state.py`.

---

## Files Changed

| File | Action |
|------|--------|
| `mcp_server/mock_regulations.json` | Expand: add entries for all 40 CFPB issue types |
| `src/tools/mcp_policy_client.py` | Fix: relative → absolute server path |
| `src/graph/langgraph_state.py` | Add: `triage_flag`, `triage_reason` fields |
| `src/graph/nodes.py` | Add: triage computation in `issue_classifier_node`; fix stale docstring |
| `src/graph/response_loop.py` | Delete |
| `src/graph/routing.py` | Delete |
| `src/graph/interrupts.py` | Delete |
| `src/graph/state.py` | Delete |

---

## What Does NOT Change

- Graph topology (nodes, edges, conditional routing) — unchanged
- All agent logic, prompts, LLM calls — unchanged
- `mcp_server/server.py` logic — unchanged (it already handles the normalized keys correctly)
- `ui/review.py`, `ui/dashboard_state.py` — untouched (UI layer, out of scope)
- `ui/runtime.py` — untouched (legacy UI path, out of scope)
