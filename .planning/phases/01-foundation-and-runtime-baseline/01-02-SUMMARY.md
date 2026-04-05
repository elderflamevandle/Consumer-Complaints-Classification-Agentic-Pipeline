---
phase: 01-foundation-and-runtime-baseline
plan: "02"
subsystem: api
tags: [groq, fallback, retry, timeout, budget, reliability]
requires:
  - phase: 01-01
    provides: Runtime config and baseline tooling
provides:
  - Deterministic model registry with locked fallback chain
  - Groq client wrapper with retry, timeout, fallback, and budget degrade hooks
  - Regression tests and optional live smoke execution path
affects: [phase-02-intake, phase-03-remediation, agent-runtime]
tech-stack:
  added: [openai-compatible transport, pydantic schema contracts]
  patterns: [centralized llm policy layer, scripted transport testing]
key-files:
  created:
    - src/llm/models.py
    - src/llm/client.py
    - src/llm/rate_limiter.py
    - src/schemas/classification.py
    - scripts/smoke_groq.py
    - tests/test_llm_client.py
  modified: []
key-decisions:
  - "Kept retry/fallback decisioning in a single client abstraction to prevent policy drift."
  - "Used injectable transport and sleep hooks for deterministic retry/fallback tests."
patterns-established:
  - "Pattern: fallback and timeout policy is validated through scripted failure classes."
  - "Pattern: budget degrade decision is explicit and testable before model selection."
requirements-completed: [AGT-01]
duration: 42min
completed: 2026-04-05
---

# Phase 1 Plan 02 Summary

**Shipped a deterministic Groq reliability layer with locked model chain fallback, retry/timeout policy, and budget-aware degradation hooks.**

## Performance

- **Duration:** 42 min
- **Started:** 2026-04-05T12:56:00-04:00
- **Completed:** 2026-04-05T13:38:00-04:00
- **Tasks:** 3
- **Files modified:** 8

## Accomplishments
- Implemented centralized model registry constants with the required fallback order.
- Implemented `GroqLLMClient` with deterministic retry/backoff, timeout handling, and fallback on 429/timeout/5xx.
- Added regression tests for fallback, retry, timeout, non-retryable error handling, and budget-degrade routing.

## Task Commits

Each task was committed atomically:

1. **Task 1: Define model registry and fallback policy constants** - `89445f7` (feat)
2. **Task 2: Build Groq client with retry timeout and budget-degrade hooks** - `c0203a4` (feat)
3. **Task 3: Add reliability tests and live smoke script** - `39100af` (test)

## Files Created/Modified
- `src/llm/models.py` - Locked model IDs and fallback-chain helper.
- `src/llm/client.py` - Retry/timeout/fallback orchestration with deterministic backoff.
- `src/llm/rate_limiter.py` - Daily token budget tracker and degrade decision helper.
- `scripts/smoke_groq.py` - Optional live endpoint smoke check with missing-key graceful skip.
- `tests/test_llm_client.py` - Policy regression tests for fallback, retry, timeout, and degrade rules.

## Decisions Made
- Added a lightweight normalized error layer so all retries use explicit trigger classes.
- Kept transport pluggable for tests to avoid network coupling while preserving production interface.

## Deviations from Plan

None - plan executed as written.

## Issues Encountered
- Ruff and mypy initially flagged style/type details in `client.py`; corrected with wrapped lines, explicit exception chaining, and typed message casting.

## User Setup Required

External services require manual configuration for live checks:
- Add `GROQ_API_KEY` in `.env` to run real API smoke tests.

## Next Phase Readiness
- Phase 2 classifier and graph nodes can call one reliability-safe client path.
- Fallback and timeout policy behavior now has dedicated regression coverage.

---
*Phase: 01-foundation-and-runtime-baseline*
*Completed: 2026-04-05*