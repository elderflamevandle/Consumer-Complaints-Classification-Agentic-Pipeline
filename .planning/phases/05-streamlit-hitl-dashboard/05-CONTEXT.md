# Phase 5: Streamlit HITL Dashboard - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase delivers the first operator-facing Streamlit dashboard for the existing complaint pipeline. It covers complaint entry, golden demo loading, live stage visibility, human-review controls, audit visibility, and token budget display. It does not add new product capabilities outside the Phase 5 roadmap boundary.

</domain>

<decisions>
## Implementation Decisions

### Operator flow and workspace shape
- Use a single control-room style workspace rather than a wizard or primarily tabbed experience.
- Keep the pipeline stage view as the visual anchor during a run.
- Human-review interruptions must stay inline on the same screen rather than moving to a separate review page.
- Stage cards should be compact by default, showing top-line signals first and deeper artifacts behind expanders.

### Complaint entry and golden demo behavior
- Default landing state is a blank complaint composer with golden-demo shortcuts nearby.
- Golden demos should load into the same main composer instead of using a separate run path.
- Loaded demos remain editable before submission.
- Present the five demos as scenario cards, not a dropdown or tab strip.

### Human review interaction
- Show approve/edit/reject controls in a sticky review panel that remains visible during interruption states.
- `Edit` should feel like inline editing within the same workspace, not a detached full-screen editor.
- Keep focused review context visible: complaint summary, interrupt reason, and current stage output.
- After reviewer action, auto-resume the same thread and show a clear status banner/toast that the pipeline is continuing.

### Telemetry, audit, and budget visibility
- Each stage card should show `model`, `latency`, and `token` usage on the main dashboard.
- Full ordered audit history belongs in a dedicated audit tab rather than the main control-room panel.
- Audit events should read in chronological pipeline order (oldest to newest).
- Daily token budget should appear as a compact always-visible header widget.

### Locked carry-forwards from prior phases
- Same-thread human-review resume remains mandatory from Phase 2.
- Phase 3 audit logging stays the source of truth for ordered event history and model metadata.
- Phase 4 response-loop behavior stays deterministic, including capped rewrites and explainer outputs.
- The UI should expose current system behavior rather than invent alternate routing or retry policies.

### Claude's Discretion
- Exact tab names, card titles, iconography, and banner wording.
- Exact arrangement of secondary panes as long as the control-room structure and priority order remain intact.
- Exact visual treatment of scenario cards, telemetry chips, and expand/collapse interactions.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/graph/state.py`: central `RoutingState`, review payloads, response-cycle traces, and final explanation slots already define the UI-facing state shape.
- `src/graph/interrupts.py`: same-thread reviewer actions (`approve`, `edit`, `reject`) already exist and should drive the dashboard interaction model.
- `src/graph/routing.py`: deterministic human-review thresholding and interrupt reasons can feed review banners and stage status.
- `src/tools/audit_logger.py`: SQLite event fetch supports audit-tab rendering with `thread_id`, `node`, `timestamp`, `model`, `latency_ms`, and `decision`.
- `src/llm/rate_limiter.py`: token budget snapshots already exist for a budget widget.
- `scripts/build_dataset.py`: produces the `demos` split that can back the five golden scenario entries for UI loading.

### Established Patterns
- Backend behavior is schema-first and deterministic; the UI should surface state and artifacts clearly instead of hiding them behind opaque presentation.
- Human review and response rewrites already preserve thread continuity; the dashboard should keep interactions inline with that model.
- No Streamlit or frontend layer exists yet, so Phase 5 defines the first operator UX pattern for the project.

### Integration Points
- Complaint submission should enter through the existing intake/classification/routing pipeline rather than a UI-only alternate path.
- Review controls should map onto current interrupt payloads and reviewer-action handlers.
- Stage telemetry should reflect actual model/token/latency values from existing agent and logging layers.
- Audit tab should read from persisted SQLite events without changing the audit contract.

</code_context>

<specifics>
## Specific Ideas

- The dashboard should feel like a live demo cockpit: one main workspace, easy-to-scan pipeline cards, and obvious reviewer actions when the system pauses.
- Golden demos should be visibly available for judges, but manual complaint entry should still feel like the primary mode.
- Audit detail should be available without cluttering the primary run experience.

</specifics>

<deferred>
## Deferred Ideas

None - discussion stayed within phase scope.

</deferred>

---

*Phase: 05-streamlit-hitl-dashboard*
*Context gathered: 2026-04-06*
