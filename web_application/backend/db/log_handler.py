"""
MongoLogHandler — thread-safe, non-blocking log handler.

Puts log records into an in-memory queue; a daemon thread drains the queue
and writes batches to MongoDB using a dedicated synchronous pymongo client
(Motor is async and cannot be used inside a background thread).

Only WARNING and above are stored by default (configurable).
If MongoDB is unavailable the handler silently drops records — logging must
never crash the application.
"""

from __future__ import annotations

import logging
import queue
import threading
import traceback
from datetime import datetime, timezone
from uuid import uuid4


class MongoLogHandler(logging.Handler):
    """Write structured log records to a MongoDB collection in a background thread."""

    def __init__(
        self,
        mongo_url: str,
        db_name: str,
        collection: str = "system_logs",
        level: int = logging.WARNING,
        batch_size: int = 50,
        flush_interval: float = 2.0,
    ) -> None:
        super().__init__(level)
        self._queue: queue.Queue[dict] = queue.Queue(maxsize=10_000)
        self._batch_size = batch_size
        self._flush_interval = flush_interval
        self._col = None
        self._connected = False

        try:
            import pymongo  # only needed here, not in the main import tree
            client = pymongo.MongoClient(
                mongo_url,
                serverSelectionTimeoutMS=3_000,
                socketTimeoutMS=5_000,
                connectTimeoutMS=3_000,
            )
            self._col = client[db_name][collection]
            # Create indexes synchronously (idempotent)
            self._col.create_index([("timestamp", pymongo.DESCENDING)])
            self._col.create_index([("level_no", pymongo.ASCENDING)])
            self._col.create_index([("logger", pymongo.ASCENDING)])
            self._connected = True
        except Exception:
            pass  # Handler degrades gracefully if Mongo is unavailable

        self._thread = threading.Thread(target=self._worker, daemon=True, name="mongo-log-writer")
        self._thread.start()

    # ── logging.Handler interface ─────────────────────────────────────────────

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._queue.put_nowait(self._format_record(record))
        except queue.Full:
            pass  # Drop silently — never block the calling thread

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _format_record(self, record: logging.LogRecord) -> dict:
        exc_text: str | None = None
        if record.exc_info:
            exc_text = "".join(traceback.format_exception(*record.exc_info))

        return {
            "_id": str(uuid4()),
            "timestamp": datetime.now(tz=timezone.utc),
            "level": record.levelname,
            "level_no": record.levelno,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "func": record.funcName,
            "line": record.lineno,
            "exc_text": exc_text,
        }

    def _worker(self) -> None:
        """Drain the queue in batches; runs in daemon thread."""
        while True:
            batch: list[dict] = []
            try:
                # Block until at least one record is available
                batch.append(self._queue.get(timeout=self._flush_interval))
                # Drain additional pending records up to batch_size
                while len(batch) < self._batch_size:
                    try:
                        batch.append(self._queue.get_nowait())
                    except queue.Empty:
                        break
            except queue.Empty:
                continue

            if batch and self._col is not None and self._connected:
                try:
                    self._col.insert_many(batch, ordered=False)
                except Exception:
                    pass  # Never propagate storage errors
