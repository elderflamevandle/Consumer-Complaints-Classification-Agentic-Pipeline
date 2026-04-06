---
status: root_cause_found
phase: 01-foundation-and-runtime-baseline
test: 2
severity: blocker
created: 2026-04-06T12:11:23.8158584-04:00
---

# Windows Make Command Unavailable

## Symptom

Running `make lint` or `make typecheck` in Windows PowerShell fails immediately with:

`The term 'make' is not recognized as the name of a cmdlet, function, script file, or operable program.`

## Expected

Phase 1 quickstart and quality-gate commands should run from a default teammate environment without undocumented setup steps.

## Root Cause

The repository standardizes baseline operations behind a `Makefile`, but does not ship a cross-platform task runner. On Windows PowerShell, `make` is not installed by default, so the documented operator path fails before the underlying Python tooling is reached.

## Evidence

- [README.md](F:/Agentic_Hackathon/README.md) leads with `make test`, `make lint`, and `make typecheck`.
- [Makefile](F:/Agentic_Hackathon/Makefile) is the only committed command dispatcher for those operations.
- The fallback note in [README.md](F:/Agentic_Hackathon/README.md) documents direct commands for Windows, but those are secondary and do not satisfy the original "standardized operator commands" contract.

## Files Involved

- [README.md](F:/Agentic_Hackathon/README.md)
- [Makefile](F:/Agentic_Hackathon/Makefile)
- [01-01-SUMMARY.md](F:/Agentic_Hackathon/.planning/phases/01-foundation-and-runtime-baseline/01-01-SUMMARY.md)

## Suggested Fix Direction

Introduce a first-class cross-platform task entrypoint, preferably a Python CLI or PowerShell-compatible wrapper, for `run`, `seed`, `eval`, `test`, `lint`, and `typecheck`. Update README to make that path primary, then keep the `Makefile` as an optional convenience on Unix-like shells.
