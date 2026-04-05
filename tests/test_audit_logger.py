from __future__ import annotations

import sqlite3
from pathlib import Path

from src.tools.audit_logger import AuditLogger


def test_node_event_written_with_required_fields(tmp_path: Path) -> None:
    logger = AuditLogger(db_path=tmp_path / 'audit.db')

    written = logger.log_node_outcome(
        thread_id='thread-3',
        node='remediator',
        model='llama-3.3-70b-versatile',
        latency_ms=124,
        decision='policy_grounded_action_plan',
        scrubbed_text='[NAME] reported repeated billing disputes.',
    )

    assert written is True
    events = logger.fetch_events(thread_id='thread-3')
    assert len(events) == 1
    event = events[0]
    assert event['thread_id'] == 'thread-3'
    assert event['node'] == 'remediator'
    assert event['model'] == 'llama-3.3-70b-versatile'
    assert event['latency_ms'] == 124
    assert event['decision'] == 'policy_grounded_action_plan'
    assert event['scrubbed_text'].startswith('[NAME]')


def test_sqlite_failure_queues_warning_without_crash(tmp_path: Path) -> None:
    def failing_connect(_: str) -> sqlite3.Connection:
        raise sqlite3.OperationalError('simulated db write failure')

    logger = AuditLogger(
        db_path=tmp_path / 'audit.db',
        connect_fn=failing_connect,
    )

    written = logger.log_node_outcome(
        thread_id='thread-3',
        node='root_cause',
        model='llama-3.3-70b-versatile',
        latency_ms=0,
        decision='diagnosis_generated',
        scrubbed_text='scrubbed complaint text',
    )

    assert written is False
    assert len(logger.warning_queue) == 1
    warning = logger.warning_queue[0]
    assert warning['thread_id'] == 'thread-3'
    assert warning['node'] == 'root_cause'
    assert 'simulated db write failure' in warning['error']

