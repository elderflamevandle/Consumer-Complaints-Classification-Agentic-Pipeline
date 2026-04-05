"""Structured SQLite audit logging for node-level pipeline decisions."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

DEFAULT_AUDIT_PATH = Path('data/audit.db')


@dataclass(frozen=True)
class AuditEvent:
    thread_id: str
    node: str
    timestamp: str
    model: str
    latency_ms: int
    decision: str
    scrubbed_text: str


class AuditLogger:
    def __init__(
        self,
        *,
        db_path: Path = DEFAULT_AUDIT_PATH,
        connect_fn: Callable[[str], sqlite3.Connection] | None = None,
    ) -> None:
        self.db_path = db_path
        self._connect_fn = connect_fn
        self.warning_queue: list[dict[str, Any]] = []

    def log_node_outcome(
        self,
        *,
        thread_id: str,
        node: str,
        model: str,
        latency_ms: int,
        decision: str,
        scrubbed_text: str = '',
        timestamp: str | None = None,
    ) -> bool:
        event = AuditEvent(
            thread_id=thread_id,
            node=node,
            timestamp=timestamp or datetime.now(UTC).isoformat(),
            model=model,
            latency_ms=max(int(latency_ms), 0),
            decision=decision,
            scrubbed_text=scrubbed_text,
        )

        try:
            with self._connect() as connection:
                self._ensure_schema(connection)
                connection.execute(
                    (
                        'INSERT INTO node_events('
                        'thread_id,node,timestamp,model,latency_ms,decision,scrubbed_text'
                        ') VALUES (?, ?, ?, ?, ?, ?, ?)'
                    ),
                    (
                        event.thread_id,
                        event.node,
                        event.timestamp,
                        event.model,
                        event.latency_ms,
                        event.decision,
                        event.scrubbed_text,
                    ),
                )
                connection.commit()
            return True
        except Exception as error:
            self.warning_queue.append(
                {
                    'timestamp': datetime.now(UTC).isoformat(),
                    'error': str(error),
                    'thread_id': thread_id,
                    'node': node,
                    'decision': decision,
                }
            )
            return False

    def fetch_events(self, *, thread_id: str | None = None) -> list[dict[str, Any]]:
        if not self.db_path.exists():
            return []

        with self._connect() as connection:
            self._ensure_schema(connection)
            if thread_id is None:
                cursor = connection.execute(
                    (
                        'SELECT thread_id,node,timestamp,model,latency_ms,decision,scrubbed_text '
                        'FROM node_events ORDER BY id ASC'
                    )
                )
            else:
                cursor = connection.execute(
                    (
                        'SELECT thread_id,node,timestamp,model,latency_ms,decision,scrubbed_text '
                        'FROM node_events WHERE thread_id = ? ORDER BY id ASC'
                    ),
                    (thread_id,),
                )
            rows = cursor.fetchall()

        events: list[dict[str, Any]] = []
        for row in rows:
            events.append(
                {
                    'thread_id': row[0],
                    'node': row[1],
                    'timestamp': row[2],
                    'model': row[3],
                    'latency_ms': row[4],
                    'decision': row[5],
                    'scrubbed_text': row[6],
                }
            )
        return events

    def _connect(self) -> sqlite3.Connection:
        if self._connect_fn is not None:
            return self._connect_fn(str(self.db_path))
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(str(self.db_path))

    @staticmethod
    def _ensure_schema(connection: sqlite3.Connection) -> None:
        connection.execute(
            (
                'CREATE TABLE IF NOT EXISTS node_events ('
                'id INTEGER PRIMARY KEY AUTOINCREMENT,'
                'thread_id TEXT NOT NULL,'
                'node TEXT NOT NULL,'
                'timestamp TEXT NOT NULL,'
                'model TEXT NOT NULL,'
                'latency_ms INTEGER NOT NULL,'
                'decision TEXT NOT NULL,'
                'scrubbed_text TEXT NOT NULL'
                ')'
            )
        )

