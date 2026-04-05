---
phase: 1
slug: foundation-and-runtime-baseline
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-05
---

# Phase 1 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + ruff + mypy |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest -q tests/test_smoke.py tests/test_llm_client.py` |
| **Full suite command** | `uv run pytest -q && uv run ruff check . && uv run mypy src` |
| **Estimated runtime** | ~45 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest -q tests/test_smoke.py tests/test_llm_client.py`
- **After every plan wave:** Run `uv run pytest -q && uv run ruff check . && uv run mypy src`
- **Before `$gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 1 | OPS-01 | integration | `uv run pytest -q tests/test_smoke.py` | ? | ? pending |
| 1-01-02 | 01 | 1 | OPS-01 | lint/type | `uv run ruff check . && uv run mypy src` | ? | ? pending |
| 1-01-03 | 01 | 1 | OPS-01 | docs/runbook | `uv run pytest -q tests/test_smoke.py` | ? | ? pending |
| 1-02-01 | 02 | 2 | AGT-01 | unit | `uv run pytest -q tests/test_llm_client.py::test_model_registry` | ? | ? pending |
| 1-02-02 | 02 | 2 | AGT-01 | unit | `uv run pytest -q tests/test_llm_client.py::test_retry_and_fallback` | ? | ? pending |
| 1-02-03 | 02 | 2 | AGT-01 | integration | `uv run pytest -q tests/test_llm_client.py::test_budget_degrade_policy` | ? | ? pending |
| 1-03-01 | 03 | 2 | DATA-01 | data | `uv run pytest -q tests/test_data_pipeline.py::test_sampling_split` | ? | ? pending |
| 1-03-02 | 03 | 2 | DATA-02 | data | `uv run pytest -q tests/test_data_pipeline.py::test_stale_detection` | ? | ? pending |
| 1-03-03 | 03 | 2 | DATA-02 | integration | `uv run pytest -q tests/test_data_pipeline.py::test_seed_manifest_written` | ? | ? pending |

*Status: ? pending � ? green � ? red � ?? flaky*

---

## Wave 0 Requirements

Existing infrastructure will be created in Plan 01 before other plans run.

- [x] `tests/test_smoke.py` - bootstrap sanity checks
- [x] `tests/conftest.py` - shared fixtures baseline
- [x] `pytest/ruff/mypy` config in `pyproject.toml`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live Groq smoke check with real API key | AGT-01 | Requires external key provisioning | Set `GROQ_API_KEY`, run `uv run python scripts/smoke_groq.py` and confirm JSON output |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
