"""Human-review interrupt payload handling and same-thread resume transitions."""

from __future__ import annotations

from src.graph.state import ReviewDecision, ReviewInterruptPayload, RoutingState


class InterruptError(ValueError):
    pass


def get_interrupt_payload(state: RoutingState) -> ReviewInterruptPayload:
    if state.interrupt_payload is None:
        raise InterruptError('No interrupt payload available for current state')
    return state.interrupt_payload


def apply_reviewer_action(state: RoutingState, decision: ReviewDecision) -> RoutingState:
    thread_id = state.thread_id
    events = list(state.events)

    if decision.action == 'approve':
        events.append(f'{thread_id}:review_approved')
        return state.model_copy(
            update={
                'route': 'continue',
                'review_required': False,
                'review_action': 'approve',
                'events': events,
            }
        )

    if decision.action == 'edit':
        if decision.edited_classification is None:
            raise InterruptError('Edited classification is required for edit action')
        events.append(f'{thread_id}:review_edited')
        return state.model_copy(
            update={
                'classification': decision.edited_classification,
                'route': 'continue',
                'review_required': False,
                'review_action': 'edit',
                'events': events,
            }
        )

    events.append(f'{thread_id}:review_rejected')
    return state.model_copy(
        update={
            'route': 'rejected',
            'review_required': False,
            'review_action': 'reject',
            'events': events,
        }
    )