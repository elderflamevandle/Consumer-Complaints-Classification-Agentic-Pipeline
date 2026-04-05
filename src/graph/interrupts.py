"""Human-review interrupt payload handling and same-thread resume transitions."""

from __future__ import annotations

from src.graph.state import ReviewDecision, ReviewInterruptPayload, RoutingState
from src.tools.audit_logger import AuditLogger


class InterruptError(ValueError):
    pass


def get_interrupt_payload(state: RoutingState) -> ReviewInterruptPayload:
    if state.interrupt_payload is None:
        raise InterruptError('No interrupt payload available for current state')
    return state.interrupt_payload


def apply_reviewer_action(
    state: RoutingState,
    decision: ReviewDecision,
    *,
    audit_logger: AuditLogger | None = None,
    latency_ms: int = 0,
) -> RoutingState:
    thread_id = state.thread_id
    events = list(state.events)
    logged_nodes = list(state.last_logged_nodes)

    if decision.action == 'approve':
        events.append(f'{thread_id}:review_approved')
        if audit_logger is not None:
            wrote = audit_logger.log_node_outcome(
                thread_id=thread_id,
                node='review_interrupt',
                model='human-review',
                latency_ms=latency_ms,
                decision='review_approved',
                scrubbed_text=state.intake.scrubbed_text,
            )
            if wrote:
                logged_nodes.append('review_interrupt')
        return state.model_copy(
            update={
                'route': 'continue',
                'review_required': False,
                'review_action': 'approve',
                'events': events,
                'last_logged_nodes': logged_nodes,
            }
        )

    if decision.action == 'edit':
        if decision.edited_classification is None:
            raise InterruptError('Edited classification is required for edit action')
        events.append(f'{thread_id}:review_edited')
        if audit_logger is not None:
            wrote = audit_logger.log_node_outcome(
                thread_id=thread_id,
                node='review_interrupt',
                model='human-review',
                latency_ms=latency_ms,
                decision='review_edited',
                scrubbed_text=state.intake.scrubbed_text,
            )
            if wrote:
                logged_nodes.append('review_interrupt')
        return state.model_copy(
            update={
                'classification': decision.edited_classification,
                'route': 'continue',
                'review_required': False,
                'review_action': 'edit',
                'events': events,
                'last_logged_nodes': logged_nodes,
            }
        )

    events.append(f'{thread_id}:review_rejected')
    if audit_logger is not None:
        wrote = audit_logger.log_node_outcome(
            thread_id=thread_id,
            node='review_interrupt',
            model='human-review',
            latency_ms=latency_ms,
            decision='review_rejected',
            scrubbed_text=state.intake.scrubbed_text,
        )
        if wrote:
            logged_nodes.append('review_interrupt')
    return state.model_copy(
        update={
            'route': 'rejected',
            'review_required': False,
            'review_action': 'reject',
            'events': events,
            'last_logged_nodes': logged_nodes,
        }
    )
