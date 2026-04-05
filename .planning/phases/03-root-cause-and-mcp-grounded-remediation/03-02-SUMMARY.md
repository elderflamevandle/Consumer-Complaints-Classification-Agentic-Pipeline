---
phase: 03-root-cause-and-mcp-grounded-remediation
plan: "02"
subsystem: api
tags: [mcp, remediation, policy-grounding, agt-04, sla]
requires:
  - phase: 03-01
    provides: Structured diagnosis and evidence outputs for remediation context
provides:
  - External MCP policy server exposing get_sla_requirements
  - MCP client adapter with required-field validation and safe unavailable fallback
  - Remediator agent that enforces pre-action policy lookup
affects: [phase-03-03-audit-logging, phase-04-response-loop, phase-05-hitl]
tech-stack:
  added: [local MCP server boundary, subprocess-based MCP client adapter]
  patterns: [mandatory pre-action tool gate, policy-unavailable fail-safe route]
key-files:
  created:
    - mcp_server/__init__.py
    - mcp_server/server.py
    - mcp_server/mock_regulations.json
    - src/tools/mcp_policy_client.py
    - src/agents/remediator.py
    - tests/test_remediator_mcp.py
  modified: []
key-decisions:
  - "Implemented a process boundary for policy lookup by invoking the MCP server script via subprocess."
  - "Remediator returns POLICY_UNAVAILABLE and human-review routing when policy retrieval is missing or invalid."
patterns-established:
  - "Pattern: MCP responses are validated against required fields before any downstream agent action."
  - "Pattern: remediator tracks mcp -> llm call ordering to preserve AGT-04 guarantees."
requirements-completed: [AGT-04]
duration: 24min
completed: 2026-04-05
---

# Phase 3 Plan 02 Summary

**Implemented AGT-04 policy-grounded remediation with a concrete MCP boundary and deterministic unavailable-policy fallback behavior.**

## Performance

- **Duration:** 24 min
- **Started:** 2026-04-05T16:10:00-04:00
- **Completed:** 2026-04-05T16:34:00-04:00
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments
- Added local MCP policy server contract with `get_sla_requirements(issue_type, state_code)` and deterministic regulation payloads.
- Added MCP client adapter that validates required fields (`sla_window`, `required_actions`, `regulatory_basis`).
- Added remediator agent that blocks action planning until MCP policy data is available and validated.
- Added AGT-04 regression tests for call order, unavailable-policy fallback, and policy citation coverage.

## Task Commits

Each task was committed atomically:

1. **Task 1: Build FastMCP policy server contract** - `9e35174` (feat)
2. **Task 2: Implement MCP policy client wrapper with guardrails** - `cd378b5` (feat)
3. **Task 3: Implement remediator agent with policy citations and AGT-04 tests** - `1bc434e` (feat/test)

## Files Created/Modified
- `mcp_server/server.py` - Local MCP-style tool endpoint for SLA requirements.
- `mcp_server/mock_regulations.json` - Deterministic policy corpus by issue and state.
- `src/tools/mcp_policy_client.py` - Tool invocation + required-field validation wrapper.
- `src/agents/remediator.py` - Policy-gated remediation orchestration.
- `tests/test_remediator_mcp.py` - AGT-04 regression suite.

## Decisions Made
- Used subprocess invocation for MCP boundary to keep runtime dependency-free while preserving process isolation.
- Standardized unavailable-policy behavior to `POLICY_UNAVAILABLE` + `human_review` route.

## Deviations from Plan

None - plan executed as written.

## Issues Encountered

None.

## User Setup Required

None - no additional external setup beyond existing environment.

## Next Phase Readiness
- Audit logging can now capture policy-grounded vs policy-unavailable remediator outcomes.
- Phase 4 writer/auditor loop can consume structured remediation action plans and citations.

---
*Phase: 03-root-cause-and-mcp-grounded-remediation*
*Completed: 2026-04-05*
