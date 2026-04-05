---
phase: 2
slug: intake-intelligence-and-classification-routing
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-05
---

# Phase 2 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + ruff + mypy |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest -q tests/test_intake_pipeline.py tests/test_classifier_agent.py` |
| **Full suite command** | `uv run pytest -q && uv run ruff check . && uv run mypy src` |
| **Estimated runtime** | ~60 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest -q tests/test_intake_pipeline.py tests/test_classifier_agent.py`
- **After every plan wave:** Run `uv run pytest -q && uv run ruff check . && uv run mypy src`
- **Before `$gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 75 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 2-01-01 | 01 | 1 | FLOW-01 | unit | `uv run pytest -q tests/test_intake_pipeline.py::test_pii_scrub_before_llm` | ? | ? pending |
| 2-01-02 | 01 | 1 | DATA-04 | unit | `uv run pytest -q tests/test_intake_pipeline.py::test_receipt_merge_contract` | ? | ? pending |
| 2-01-03 | 01 | 1 | FLOW-01 | integration | `uv run pytest -q tests/test_intake_pipeline.py::test_low_confidence_scrub_routes_or_warns` | ? | ? pending |
| 2-02-01 | 02 | 2 | AGT-02 | unit | `uv run pytest -q tests/test_classifier_agent.py::test_classifier_strict_schema` | ? | ? pending |
| 2-02-02 | 02 | 2 | AGT-02 | unit | `uv run pytest -q tests/test_classifier_agent.py::test_invalid_json_repair_retry_then_fallback` | ? | ? pending |
| 2-02-03 | 02 | 2 | AGT-02 | unit | `uv run pytest -q tests/test_classifier_agent.py::test_missing_confidence_keyword_heuristic` | ? | ? pending |
| 2-03-01 | 03 | 3 | FLOW-02 | unit | `uv run pytest -q tests/test_routing_interrupts.py::test_route_low_confidence_or_high_risk` | ? | ? pending |
| 2-03-02 | 03 | 3 | FLOW-02 | integration | `uv run pytest -q tests/test_routing_interrupts.py::test_resume_same_thread_after_review` | ? | ? pending |
| 2-03-03 | 03 | 3 | FLOW-02 | integration | `uv run pytest -q tests/test_routing_interrupts.py::test_reviewer_actions_approve_edit_reject` | ? | ? pending |

*Status: ? pending · ? green · ? red · ?? flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_intake_pipeline.py` - intake safety and receipt merge contracts
- [ ] `tests/test_classifier_agent.py` - AGT-02 schema/retry contracts
- [ ] `tests/test_routing_interrupts.py` - FLOW-02 routing and resume contracts

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Reviewer unavailable warning path | FLOW-02 | Depends on runtime/session reviewer state toggles | Disable reviewer availability, submit low-confidence case, confirm warning + continuation |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 75s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending