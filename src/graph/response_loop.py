"""Deterministic writer-auditor response loop for Phase 4."""

from __future__ import annotations

from src.agents.auditor import AuditorAgent
from src.agents.remediator import RemediationResult
from src.agents.writer import WriterAgent
from src.graph.state import ResponseCycleTrace, RoutingState
from src.schemas.auditor import AuditVerdict
from src.schemas.root_cause import RootCauseResult

MAX_REWRITE_ATTEMPTS = 2
MAX_MESSAGE_HISTORY = 6


def execute_response_loop(
    state: RoutingState,
    *,
    diagnosis: RootCauseResult,
    remediation: RemediationResult,
    writer: WriterAgent,
    auditor: AuditorAgent,
    max_rewrites: int = MAX_REWRITE_ATTEMPTS,
) -> RoutingState:
    current = state

    while True:
        draft = writer.compose_response(
            complaint_text=current.intake.scrubbed_text,
            classification=current.classification,
            diagnosis=diagnosis,
            remediation=remediation,
            unresolved_issues=current.unresolved_issues,
            thread_id=current.thread_id,
        )
        audit = auditor.review_response(
            draft=draft,
            remediation=remediation,
            thread_id=current.thread_id,
        )
        current = _record_cycle(current, draft=draft, audit=audit)

        if audit.verdict == AuditVerdict.PASS:
            events = list(current.events)
            events.append(f'{current.thread_id}:response_pass')
            return current.model_copy(
                update={
                    'route': 'continue',
                    'review_required': False,
                    'latest_response_draft': draft,
                    'unresolved_issues': [],
                    'response_loop_status': 'approved',
                    'final_audit': audit,
                    'events': events,
                }
            )

        if current.rewrite_count >= max_rewrites:
            events = list(current.events)
            events.append(f'{current.thread_id}:response_escalated')
            return current.model_copy(
                update={
                    'route': 'human_review',
                    'review_required': True,
                    'latest_response_draft': draft,
                    'unresolved_issues': list(audit.must_fix_items),
                    'response_loop_status': 'escalated',
                    'final_audit': audit,
                    'events': events,
                }
            )

        next_count = current.rewrite_count + 1
        events = list(current.events)
        events.append(f'{current.thread_id}:response_rewrite_{next_count}')
        current = current.model_copy(
            update={
                'latest_response_draft': draft,
                'unresolved_issues': list(audit.must_fix_items),
                'rewrite_count': next_count,
                'response_loop_status': 'needs_rewrite',
                'final_audit': audit,
                'events': events,
            }
        )


def _record_cycle(
    state: RoutingState,
    *,
    draft,
    audit,
) -> RoutingState:
    cycle_number = len(state.response_cycles) + 1
    history = list(state.message_history)
    history.extend(
        [
            f'writer:{draft.resolution_statement}',
            f'auditor:{audit.critique_summary}',
        ]
    )
    trace = ResponseCycleTrace(
        cycle_number=cycle_number,
        verdict=audit.verdict.value,
        fail_codes=[code.value for code in audit.reason_codes],
        critique_summary=audit.critique_summary,
    )
    return state.model_copy(
        update={
            'latest_response_draft': draft,
            'message_history': history[-MAX_MESSAGE_HISTORY:],
            'response_cycles': [*state.response_cycles, trace],
        }
    )
