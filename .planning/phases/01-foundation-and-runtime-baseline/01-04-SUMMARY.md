---
phase: 01-foundation-and-runtime-baseline
plan: "04"
subsystem: infra
tags: [cli, windows, powershell, uv, argparse, make, testing, docs]
requires:
  - phase: 01-01
    provides: Shared baseline runtime commands and teammate setup flow
provides:
  - Cross-platform `scripts/tasks.py` entrypoint for baseline operator commands
  - Makefile delegation that preserves Unix shorthand without requiring GNU Make
  - Regression tests covering task mapping, dispatch order, and invalid command behavior
affects: [phase-05-ui, phase-06-eval, onboarding, operator-commands]
tech-stack:
  added: [argparse task CLI, subprocess-based command dispatch]
  patterns: [single-source task contract, wrapper Makefile targets, contract-style CLI regression tests]
key-files:
  created:
    - scripts/tasks.py
    - tests/test_task_runner.py
  modified:
    - Makefile
    - README.md
key-decisions:
  - "Standardized baseline operator commands behind `scripts/tasks.py` so Windows PowerShell and Unix shells share the same primary entrypoint."
  - "Kept `Makefile` as a thin optional wrapper that delegates to the Python task runner to prevent command drift."
patterns-established:
  - "Pattern: repo-level operator commands live in `scripts/tasks.py`, and docs or shell wrappers point to that script instead of duplicating behavior."
  - "Pattern: task entrypoint regressions are guarded with focused dispatch-contract tests that mock subprocess execution."
requirements-completed: [OPS-01]
duration: 6min
completed: 2026-04-06
---

# Phase 1 Plan 04 Summary

**Cross-platform `scripts/tasks.py` CLI with Makefile delegation, README-first PowerShell flow, and regression coverage for baseline operator commands.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-04-06T16:52:56Z
- **Completed:** 2026-04-06T16:59:11Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- Added a first-class Python task runner for `run`, `seed`, `eval`, `test`, `lint`, and `typecheck`.
- Reworked the README so the cross-platform task runner is the primary teammate path and `make` is optional convenience only.
- Added focused regression tests for command mapping, dispatch order, subprocess exit handling, and invalid CLI usage.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add cross-platform task runner for baseline operator commands** - `8737fb6` (test), `92fb4dc` (feat)
2. **Task 2: Update README quickstart to make the cross-platform path primary** - `10cf625` (feat)
3. **Task 3: Add regression coverage for task dispatch and command contract** - `ca4171a` (test), `978e35b` (fix)

**Verification fix:** `7374672` (fix)

## Files Created/Modified
- `scripts/tasks.py` - `argparse` CLI and subprocess dispatcher for baseline repository tasks.
- `tests/test_task_runner.py` - Contract tests for supported task names, command mapping, dispatch sequencing, and invalid command behavior.
- `Makefile` - Optional Unix convenience wrapper that delegates every target to `scripts/tasks.py`.
- `README.md` - Cross-platform quickstart and command flow anchored on the Python task runner.

## Decisions Made
- Introduced `scripts/tasks.py` as the single source of truth for operator commands instead of asking Windows users to translate `make` targets manually.
- Preserved `make` as a thin wrapper rather than removing it so Unix-friendly shorthand remains available without becoming a hidden prerequisite.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Resolved Ruff line-length failures introduced by the new task runner contract**
- **Found during:** Plan-level verification
- **Issue:** `uv run python scripts/tasks.py lint` failed on long command literals and one long test signature added in this plan.
- **Fix:** Extracted the shared runtime command into a constant and wrapped the long regression-test function signature.
- **Files modified:** `scripts/tasks.py`, `tests/test_task_runner.py`
- **Verification:** `uv run python scripts/tasks.py lint`, `uv run python scripts/tasks.py test`, `uv run python scripts/tasks.py typecheck`, and `uv run pytest -q tests/test_task_runner.py`
- **Committed in:** `7374672`

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** The fix was required to satisfy the documented quality-gate commands. No scope creep.

## Issues Encountered
- A transient `.git/index.lock` blocked the first RED-test commit attempt. The lock was gone on retry, and the repository committed normally afterward.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Future phases can rely on `uv run python scripts/tasks.py <command>` as the documented baseline operator contract across shells.
- Phase 5 planning can proceed without revisiting the Windows PowerShell command gap.

## Self-Check: PASSED
- Verified `.planning/phases/01-foundation-and-runtime-baseline/01-04-SUMMARY.md` exists.
- Verified task and verification-fix commits `8737fb6`, `92fb4dc`, `10cf625`, `ca4171a`, `978e35b`, and `7374672` exist in git history.

---
*Phase: 01-foundation-and-runtime-baseline*
*Completed: 2026-04-06*
