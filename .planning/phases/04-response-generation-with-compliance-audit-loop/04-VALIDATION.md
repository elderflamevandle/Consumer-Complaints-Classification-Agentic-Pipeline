---
phase: 4
slug: response-generation-with-compliance-audit-loop
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-05
---

# Phase 4 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + ruff + mypy |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest -q tests/test_response_writer.py tests/test_auditor_loop.py tests/test_explainer_agent.py tests/test_phase4_state.py` |
| **Full suite command** | `uv run pytest -q && uv run ruff check . && uv run mypy src` |
| **Estimated runtime** | ~85 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest -q tests/test_response_writer.py tests/test_auditor_loop.py tests/test_explainer_agent.py tests/test_phase4_state.py`
- **After every plan wave:** Run `uv run pytest -q && uv run ruff check . && uv run mypy src`
- **Before `$gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 90 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 4-01-01 | 01 | 1 | AGT-05 | unit | `uv run pytest -q tests/test_response_writer.py::test_writer_generates_four_block_response` | ? | ? pending |
| 4-01-02 | 01 | 1 | AGT-05 | unit | `uv run pytest -q tests/test_response_writer.py::test_writer_includes_resolution_statement_and_policy_labels` | ? | ? pending |
| 4-01-03 | 01 | 1 | AGT-05 | integration | `uv run pytest -q tests/test_response_writer.py::test_writer_blocks_overcommitment_language` | ? | ? pending |
| 4-02-01 | 02 | 2 | AGT-06 | unit | `uv run pytest -q tests/test_auditor_loop.py::test_auditor_returns_reason_coded_fail` | ? | ? pending |
| 4-02-02 | 02 | 2 | AGT-06 | integration | `uv run pytest -q tests/test_auditor_loop.py::test_fail_routes_back_to_writer_until_retry_cap` | ? | ? pending |
| 4-02-03 | 02 | 2 | AGT-06 | integration | `uv run pytest -q tests/test_auditor_loop.py::test_pass_routes_continue_and_logs_writer_auditor_events` | ? | ? pending |
| 4-03-01 | 03 | 3 | FLOW-03 | unit | `uv run pytest -q tests/test_phase4_state.py::test_response_loop_state_carries_unresolved_issues_across_rewrites` | ? | ? pending |
| 4-03-02 | 03 | 3 | AGT-07 | unit | `uv run pytest -q tests/test_explainer_agent.py::test_explainer_outputs_stage_chain_bullets` | ? | ? pending |
| 4-03-03 | 03 | 3 | AGT-07,FLOW-03 | integration | `uv run pytest -q tests/test_explainer_agent.py::test_explainer_uses_final_artifacts_not_raw_input tests/test_phase4_state.py::test_cycle_trace_persists_verdict_codes_and_final_resolution` | ? | ? pending |

*Status: ? pending - ? green - ? red - ?? flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_response_writer.py` - AGT-05 response structure and guardrail coverage
- [ ] `tests/test_auditor_loop.py` - AGT-06 verdict, routing, and retry-cap coverage
- [ ] `tests/test_explainer_agent.py` - AGT-07 stage-chain explanation coverage
- [ ] `tests/test_phase4_state.py` - FLOW-03 bounded critique-memory coverage

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Final customer draft reads naturally after one failed audit and one rewrite | AGT-05, AGT-06 | Tone quality and customer readability still need a human judgment pass | Run one seeded complaint through writer -> auditor -> rewrite loop, confirm the final draft keeps the 4-block structure, cites policy labels, and resolves prior fail codes without introducing guarantees |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 90s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
