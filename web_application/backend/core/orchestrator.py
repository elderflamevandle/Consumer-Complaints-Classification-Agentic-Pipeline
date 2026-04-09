"""
Orchestrator that wraps the fincomplaint-ai library.
"""

from typing import Dict, Any, Optional
import asyncio
from datetime import datetime, timedelta
import threading
import time

# Import from fincomplaint-ai library (assuming it's installed or in path)
from fincomplaint_ai import ComplaintOrchestrator as FinComplaintOrchestrator

from ..config import settings

class ComplaintOrchestrator:
    """Thread-safe wrapper around fincomplaint-ai orchestrator."""

    def __init__(self):
        self.fin_orchestrator = FinComplaintOrchestrator(
            persist_dir=settings.thread_persist_dir
        )
        self.active_threads: Dict[str, Dict[str, Any]] = {}
        self.thread_lock = threading.Lock()
        self._start_cleanup_thread()

    def _start_cleanup_thread(self):
        """Start background thread to clean up expired threads."""
        def cleanup_worker():
            while True:
                self._cleanup_expired_threads()
                time.sleep(3600)  # Check every hour

        thread = threading.Thread(target=cleanup_worker, daemon=True)
        thread.start()

    def _cleanup_expired_threads(self):
        """Remove threads older than TTL."""
        cutoff = datetime.utcnow() - timedelta(hours=settings.thread_ttl_hours)
        with self.thread_lock:
            expired = [
                thread_id for thread_id, data in self.active_threads.items()
                if data.get("created_at", datetime.min) < cutoff
            ]
            for thread_id in expired:
                del self.active_threads[thread_id]

    async def submit_complaint(self, complaint_text: str, demo_id: Optional[str] = None) -> str:
        """Submit a complaint and return thread_id."""
        # For now, treat demo_id as part of complaint_text if provided
        if demo_id:
            complaint_text = f"Demo {demo_id}: {complaint_text}"

        thread_id = await self.fin_orchestrator.submit_complaint(complaint_text)

        with self.thread_lock:
            self.active_threads[thread_id] = {
                "created_at": datetime.utcnow(),
                "status": "pending"
            }

        return thread_id

    async def get_status(self, thread_id: str) -> Dict[str, Any]:
        """Get current status of a complaint thread."""
        try:
            snapshot = await self.fin_orchestrator.get_status(thread_id)
            return self._snapshot_to_dict(snapshot)
        except ValueError:
            raise ValueError(f"Thread {thread_id} not found")

    async def submit_review_action(
        self,
        thread_id: str,
        action: str,
        edit_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """Submit a review action (approve/edit/reject)."""
        try:
            snapshot = await self.fin_orchestrator.submit_review_action(
                thread_id, action, edit_text
            )
            return self._snapshot_to_dict(snapshot)
        except ValueError:
            raise ValueError(f"Thread {thread_id} not found")

    async def get_audit_events(self, thread_id: str) -> Dict[str, Any]:
        """Get audit events for a thread."""
        try:
            events = await self.fin_orchestrator.get_audit_events(thread_id)
            return {
                "thread_id": thread_id,
                "events": events,
                "total_events": len(events)
            }
        except ValueError:
            raise ValueError(f"Thread {thread_id} not found")

    async def stream_updates(self, thread_id: str):
        """Stream live updates for WebSocket."""
        try:
            async for update in self.fin_orchestrator.stream_updates(thread_id):
                yield update
        except ValueError:
            raise ValueError(f"Thread {thread_id} not found")

    def _snapshot_to_dict(self, snapshot) -> Dict[str, Any]:
        """Convert ThreadSnapshot to dict."""
        return {
            "thread_id": snapshot.thread_id,
            "complaint_source": snapshot.complaint_source,
            "current_stage": snapshot.current_stage,
            "status": snapshot.status,
            "stages": snapshot.stages,
            "review_state": snapshot.review_state,
            "response_draft": snapshot.response_draft,
            "explanation": snapshot.explanation,
            "updated_at": snapshot.updated_at.isoformat()
        }