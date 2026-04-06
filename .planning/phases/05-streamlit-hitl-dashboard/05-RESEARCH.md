# Phase 5: Streamlit HITL Dashboard - Research

**Researched:** 2026-04-06
**Domain:** Streamlit control-room UI + pipeline telemetry + inline human review for the existing complaint workflow
**Confidence:** MEDIUM

<user_constraints>
## User Constraints (from 05-CONTEXT.md)

### Locked Decisions
- The dashboard must be a single control-room workspace, not a wizard or tab-first UI.
- Pipeline stage cards are the visual anchor during a run.
- Human-review interruptions stay inline on the same screen.
- Stage cards should be compact by default and reveal deeper detail through expanders.
- Landing state is a blank complaint composer with nearby golden-demo shortcuts.
- Golden demos load into the same editable composer and share the same submission path as free-text complaints.
- The five golden demos should be presented as scenario cards.
- Review uses a sticky action panel with approve/edit/reject controls.
- `Edit` should feel inline, not like a detached full-screen editor.
- Review context should stay focused on complaint summary, interrupt reason, and current stage output.
- After reviewer action, the same thread should auto-resume and show a clear status banner/toast.
- Main stage cards should show `model`, `latency`, and `token` usage.
- Full audit history belongs in a dedicated audit tab and should be ordered chronologically.
- Daily token budget belongs in a compact always-visible header widget.

### Carry-forward Constraints
- Same-thread resume behavior from Phase 2 is mandatory.
- SQLite audit logging from Phase 3 remains the source of truth for ordered event history.
- Phase 4 response-loop and explainability behavior remain deterministic and should be surfaced, not redefined.
- The UI must expose actual pipeline behavior rather than introduce alternate routing or retry policies.

### Claude's Discretion
- Exact tab names, stage-card titles, banner copy, and iconography.
- Exact arrangement of secondary panes and expanders.
- Exact implementation details for caching, helper modules, and visual polish.

</user_constraints>

<research_summary>
## Summary

Phase 5 should be planned around a dedicated dashboard runtime facade, not direct agent orchestration inside the Streamlit page script.

Recommended strategy:
1. Create a thin runtime/service layer that executes the existing complaint pipeline and returns stage snapshots, review state, and UI-safe telemetry.
2. Build a Streamlit control-room shell around that runtime using session state as the live same-browser-session source of truth.
3. Keep complaint submission and review edits inside explicit forms so the app's rerun model stays predictable.
4. Surface top-line telemetry on stage cards, keep the full audit trail in its own tab, and treat token budget as a persistent header metric.
5. Use Streamlit's built-in `AppTest` framework plus pure runtime tests so UI behaviors are regression-tested without manual clicking.

Key planning implication:
- The current codebase has all major pipeline stages, interrupt payloads, audit logging, and token-budget tracking, but it does not have a single UI-safe orchestration surface. Phase 5 therefore needs both a Streamlit app and a runtime adapter layer.

</research_summary>

<standard_stack>
## Standard Stack

### Core
| Library/Module | Purpose | Why it fits this phase |
|----------------|---------|------------------------|
| `streamlit` | Control-room dashboard, forms, tabs, metrics, toast/banner feedback | Matches the roadmap's chosen UI layer and the fastest path to a demo-ready operator surface |
| `streamlit.testing.v1.AppTest` | Simulated UI testing with widget interaction and reruns | Official testing path for Streamlit apps; avoids brittle browser automation for Phase 5 |
| `st.session_state` | Per-session thread continuity, selected demo, current run snapshot, review draft state | Official Streamlit state primitive for rerun-safe app logic |
| `src/graph/state.py` + `src/graph/interrupts.py` | Existing thread, interrupt, and reviewer-action contracts | Already encode same-thread approve/edit/reject behavior |
| `src/tools/audit_logger.py` | Ordered event history for the audit tab | Already persists node, timestamp, model, latency, and decision per thread |
| `src/llm/rate_limiter.py` | Daily budget snapshot for the header widget | Already exposes used tokens, warning, and degradation thresholds |

### Supporting
| Library/Pattern | Purpose | Phase use |
|-----------------|---------|-----------|
| `st.form` | Batch complaint submission and review edits | Prevents partial reruns while composing or editing |
| `st.tabs` | Split audit detail from the main control room | Keeps the run surface focused while still exposing trace detail |
| `st.metric` | Compact budget and stage telemetry chips | Good fit for top-line operational signals |
| `st.toast` | Auto-resume confirmation after reviewer actions | Matches the desired brief status-banner behavior |
| typed runtime snapshot models | Stable app-to-runtime contract | Keeps Streamlit rendering logic thin and testable |

### Alternatives Considered
| Chosen | Alternative | Tradeoff |
|--------|-------------|----------|
| dedicated runtime facade | direct Streamlit page calling agents inline | facade is more code, but much easier to test and reason about under reruns |
| session-state control room | multi-page or stepper workflow | control room better matches the user's locked demo direction |
| shared editable composer for demos and free text | separate demo mode | shared composer reduces UI branching and test duplication |
| AppTest + runtime tests | browser E2E only | lighter-weight and better aligned with the current repo's pytest-first setup |

</standard_stack>

<architecture_patterns>
## Architecture Patterns

### Pattern 1: Dashboard Runtime Facade
- Introduce a pure-Python runtime module that owns end-to-end pipeline execution for the UI.
- The facade should orchestrate:
  - intake preparation
  - classification
  - routing / interrupt decision
  - root-cause diagnosis
  - remediation
  - response loop
  - explainer
- It should return a typed dashboard snapshot containing:
  - `thread_id`
  - complaint source (`manual` or demo id)
  - current route/status
  - stage cards with status, model, latency, and tokens
  - latest review payload (if any)
  - final response/explanation artifacts
  - audit-thread lookup key
- This keeps Streamlit page code focused on rendering and dispatching actions.

### Pattern 2: Session-State-Owned Control Room
- Streamlit officially documents session state as the way to share variables between reruns for each user session, and it also persists across pages inside a multipage app. It is therefore the right place to keep the active thread id, selected demo, current dashboard snapshot, pending reviewer edits, and resume banners.
- The same docs also warn that session state is tied to a WebSocket and resets on browser reload. Planning should therefore scope continuity to the active browser session and not imply durable resume after a tab refresh.

### Pattern 3: Form-Based Mutation Boundaries
- `st.form` batches widget values until submit. Streamlit's docs note that every form must contain a `st.form_submit_button`, that buttons cannot be added to a form, and that only the submit button may have a callback.
- Use one form for complaint submission and a separate form for inline review edits.
- Avoid mixing ephemeral button state with thread continuity.

### Pattern 4: Telemetry/Audit Split
- Main stage cards should show compact telemetry that helps a judge understand the live run: model, latency, token usage, and final stage state.
- Full audit history should come from the SQLite audit logger in chronological order.
- Streamlit's tabs docs note that tab content is computed even when inactive unless lazy rerun behavior is deliberately configured. The audit tab should therefore stay lightweight and avoid hidden expensive computation.

### Pattern 5: Callback-First Resume, Rerun as Escape Hatch
- Streamlit documents that callbacks run before the app re-executes top-to-bottom, and that `st.rerun()` halts the current run and queues an immediate rerun.
- For review actions, prefer callbacks or form submission handlers that update session state cleanly.
- Use `st.rerun()` sparingly for explicit post-action refreshes, not as the main control-flow mechanism.

### Pattern 6: First-Class App Testing
- Streamlit's official testing guide shows `AppTest.from_file(...).run()` plus widget interactions like `.click()` and `.set_value()` as the supported way to test app behavior under reruns.
- Phase 5 should key important widgets so tests can target them by semantic key instead of fragile display order.
- Use AppTest for UI structure and flow, and pure pytest unit tests for runtime adapters and session/review helpers.

</architecture_patterns>

<dont_hand_roll>
## Don't Hand-Roll

| Problem | Avoid | Use Instead |
|---------|-------|-------------|
| rerun-heavy page logic | embedding full orchestration in `streamlit_app.py` | runtime facade + thin render layer |
| brittle UI state | storing active thread in button state or temporary locals | `st.session_state` with typed helper accessors |
| duplicated input paths | separate code for demos vs manual complaint entry | one composer and one submit path |
| heavy hidden tab work | expensive pipeline recompute inside inactive tabs | cheap audit fetch/render helpers and precomputed snapshots |
| index-based UI tests | relying only on widget order | stable keys + `AppTest` selectors |

</dont_hand_roll>

<common_pitfalls>
## Common Pitfalls

### Pitfall 1: Session continuity is promised beyond what Streamlit provides
- **Risk:** users think thread state survives browser reloads.
- **Prevent with:** keep continuity scoped to the active browser session and expose the live thread id/state clearly.

### Pitfall 2: Forms and buttons are mixed incorrectly
- **Risk:** review actions or complaint submission rerun at surprising times.
- **Prevent with:** dedicated forms for submission/editing and non-form buttons only where ephemeral clicks are acceptable.

### Pitfall 3: Stage telemetry has no real source of truth
- **Risk:** UI shows placeholders or misleading metrics.
- **Prevent with:** add an explicit stage telemetry contract in the runtime layer and capture model/latency/token values from each agent call or wrapper.

### Pitfall 4: Audit tab becomes expensive or noisy
- **Risk:** tabbed UI feels sluggish and distracts from the main control room.
- **Prevent with:** keep the audit view read-only, chronological, and sourced from lightweight per-thread fetch helpers.

### Pitfall 5: Review actions restart the pipeline instead of resuming it
- **Risk:** thread continuity requirement regresses even though the UI appears correct.
- **Prevent with:** preserve the active routing state in session state and map UI actions directly onto the existing reviewer-action contract.

### Pitfall 6: UI tests couple to widget order
- **Risk:** harmless layout changes break many tests.
- **Prevent with:** use widget keys and container-scoped AppTest access rather than index-only assertions wherever possible.

</common_pitfalls>

<code_examples>
## Code Examples

### Runtime facade sketch
```python
snapshot = runtime.run_complaint(
    complaint_text=session.complaint_text,
    receipt_text=session.receipt_text,
    reviewer_available=True,
)
assert snapshot.thread_id
assert snapshot.stages["classification"].model
```

### Session-state continuity
```python
if "dashboard" not in st.session_state:
    st.session_state.dashboard = DashboardSession.new()

session = st.session_state.dashboard
session.active_thread_id = snapshot.thread_id
session.last_snapshot = snapshot
```

### Review action handler
```python
def handle_review_submit(action: str, edited_payload: dict[str, str] | None = None) -> None:
    session = st.session_state.dashboard
    session.last_snapshot = runtime.apply_review_action(
        snapshot=session.last_snapshot,
        action=action,
        edited_payload=edited_payload,
    )
    st.toast("Review submitted. Resuming thread...", icon=":material/play_arrow:")
```

### AppTest flow
```python
from streamlit.testing.v1 import AppTest

at = AppTest.from_file("app/streamlit_app.py").run()
at.button(key="demo_card_billing_error").click().run()
at.text_area(key="complaint_text").set_value("Updated complaint text").run()
at.form_submit_button(key="submit_complaint").click().run()
assert at.metric(key="daily_budget_used").value is not None
```

</code_examples>

<sota_updates>
## State of the Art (2025-2026)

- Current Streamlit docs continue to position `st.session_state`, forms, callbacks, and AppTest as the core primitives for predictable rerun-safe app logic.
- Current tabs docs expose lazy-rerun hooks, but the conservative planning choice is still to treat tabs as potentially eager and keep hidden content cheap.
- `st.metric` and `st.toast` remain appropriate for compact telemetry and brief status feedback without introducing custom frontend infrastructure.
- The lowest-risk Phase 5 implementation uses stable built-in Streamlit primitives rather than custom components or browser-heavy E2E tooling.

</sota_updates>

## Validation Architecture

Validation should cover both the pure runtime layer and the Streamlit control-room surface.

- **Per task commit (quick):**
  - `uv run pytest -q tests/test_ui_runtime.py tests/test_streamlit_app.py tests/test_review_session.py`
- **Per wave (full):**
  - `uv run pytest -q && uv run ruff check . && uv run mypy src app`

Minimum guarantees:
1. The app loads with a blank composer, five scenario cards, and a shared editable complaint path.
2. Stage cards show live status plus model/latency/token telemetry from the runtime snapshot.
3. Review actions (`approve`, `edit`, `reject`) preserve the same thread in session state and update the dashboard deterministically.
4. Audit history renders in chronological order from SQLite and the daily token budget widget reflects the tracker snapshot.

<open_questions>
## Open Questions

1. **Telemetry source granularity**
   - Decide whether to capture per-stage tokens strictly in the runtime snapshot, or also extend persisted audit records with token counts.
2. **Golden demo storage format**
   - Decide whether the five curated demos should live as a JSON data file, a typed Python module, or both.
3. **Review target abstraction**
   - Decide whether the first dashboard cut supports only the existing interrupt payload contract or introduces a more generic review-target adapter for later phases.

</open_questions>

<sources>
## Sources

### Primary local sources
- `.planning/phases/05-streamlit-hitl-dashboard/05-CONTEXT.md`
- `.planning/ROADMAP.md`
- `.planning/REQUIREMENTS.md`
- `.planning/STATE.md`
- `src/graph/state.py`
- `src/graph/interrupts.py`
- `src/graph/routing.py`
- `src/tools/audit_logger.py`
- `src/llm/rate_limiter.py`
- `tests/test_phase3_graph_logging.py`
- `src/intake/pipeline.py`

### Primary external sources
- Streamlit Session State docs: https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state
- Streamlit forms docs: https://docs.streamlit.io/develop/api-reference/execution-flow/st.form
- Streamlit rerun docs: https://docs.streamlit.io/develop/api-reference/execution-flow/st.rerun
- Streamlit tabs docs: https://docs.streamlit.io/develop/api-reference/layout/st.tabs
- Streamlit toast docs: https://docs.streamlit.io/develop/api-reference/status/st.toast
- Streamlit metric docs: https://docs.streamlit.io/develop/api-reference/data/st.metric
- Streamlit status docs: https://docs.streamlit.io/develop/api-reference/status/st.status
- Streamlit AppTest guide: https://docs.streamlit.io/develop/concepts/app-testing/get-started

</sources>

<metadata>
## Metadata

**Research scope:** Phase 5 dashboard runtime, Streamlit interaction model, and verification strategy
**Confidence breakdown:**
- Streamlit session/form/rerun patterns: HIGH
- dashboard runtime facade shape: MEDIUM
- telemetry + audit split: MEDIUM
- same-thread review continuity in the UI: MEDIUM

**Research date:** 2026-04-06
**Valid until:** 2026-05-06
</metadata>

---

*Phase: 05-streamlit-hitl-dashboard*
*Research completed: 2026-04-06*
*Ready for planning: yes*
