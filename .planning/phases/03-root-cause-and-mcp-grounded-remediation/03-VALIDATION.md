---
phase: 3
slug: root-cause-and-mcp-grounded-remediation
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-05
---

# Phase 3 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + ruff + mypy |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest -q tests/test_root_cause_agent.py tests/test_remediator_mcp.py tests/test_audit_logger.py` |
| **Full suite command** | `uv run pytest -q && uv run ruff check . && uv run mypy src` |
| **Estimated runtime** | ~75 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest -q tests/test_root_cause_agent.py tests/test_remediator_mcp.py tests/test_audit_logger.py`
- **After every plan wave:** Run `uv run pytest -q && uv run ruff check . && uv run mypy src`
- **Before `$gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 90 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 3-01-01 | 01 | 1 | AGT-03 | unit | `uv run pytest -q tests/test_root_cause_agent.py::test_retrieves_top5_similar_cases` | ? | ? pending |
| 3-01-02 | 01 | 1 | AGT-03 | unit | `uv run pytest -q tests/test_root_cause_agent.py::test_root_cause_outputs_ranked_evidence_with_citations` | ? | ? pending |
| 3-01-03 | 01 | 1 | AGT-03 | integration | `uv run pytest -q tests/test_root_cause_agent.py::test_conflicting_evidence_sets_ambiguous_flag` | ? | ? pending |
| 3-02-01 | 02 | 2 | AGT-04 | unit | `uv run pytest -q tests/test_remediator_mcp.py::test_mcp_tool_is_called_before_action_plan` | ? | ? pending |
| 3-02-02 | 02 | 2 | AGT-04 | unit | `uv run pytest -q tests/test_remediator_mcp.py::test_policy_unavailable_routes_human_review` | ? | ? pending |
| 3-02-03 | 02 | 2 | AGT-04 | integration | `uv run pytest -q tests/test_remediator_mcp.py::test_remediation_cites_required_mcp_fields` | ? | ? pending |
| 3-03-01 | 03 | 3 | FLOW-05 | unit | `uv run pytest -q tests/test_audit_logger.py::test_node_event_written_with_required_fields` | ? | ? pending |
| 3-03-02 | 03 | 3 | FLOW-05 | integration | `uv run pytest -q tests/test_audit_logger.py::test_sqlite_failure_queues_warning_without_crash` | ? | ? pending |
| 3-03-03 | 03 | 3 | FLOW-05 | integration | `uv run pytest -q tests/test_phase3_graph_logging.py::test_phase3_nodes_emit_thread_consistent_events` | ? | ? pending |

*Status: ? pending - ? green - ? red - ?? flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_root_cause_agent.py` - AGT-03 retrieval and evidence contract checks
- [ ] `tests/test_remediator_mcp.py` - AGT-04 mandatory MCP boundary checks
- [ ] `tests/test_audit_logger.py` - FLOW-05 SQLite contract and fail-open logging behavior
- [ ] `tests/test_phase3_graph_logging.py` - cross-node event consistency checks

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live MCP server discovery + tool invocation | AGT-04 | Requires process-level MCP transport and real tool handshake | Start local MCP server, run one remediation case, verify discovered tool list includes `get_sla_requirements` and output includes cited policy fields |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 90s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
