"""
WebSocket handlers for live pipeline updates.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json
import logging

from ..core.orchestrator import ComplaintOrchestrator

logger = logging.getLogger(__name__)

router = APIRouter()
orchestrator = ComplaintOrchestrator()

@router.websocket("/ws/complaints/{thread_id}")
async def complaint_websocket(websocket: WebSocket, thread_id: str):
    """WebSocket endpoint for live complaint pipeline updates."""
    await websocket.accept()

    try:
        logger.info(f"WebSocket connection established for thread {thread_id}")

        # Send initial status
        try:
            initial_status = await orchestrator.get_status(thread_id)
            await websocket.send_json({
                "type": "status_update",
                **initial_status
            })
        except ValueError:
            await websocket.send_json({
                "type": "error",
                "message": f"Thread {thread_id} not found"
            })
            await websocket.close()
            return

        # Stream live updates
        try:
            async for update in orchestrator.stream_updates(thread_id):
                await websocket.send_json({
                    "type": "stage_update",
                    **update
                })
        except Exception as e:
            logger.error(f"Error streaming updates for thread {thread_id}: {e}")
            await websocket.send_json({
                "type": "error",
                "message": "Failed to stream updates"
            })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for thread {thread_id}")
    except Exception as e:
        logger.error(f"WebSocket error for thread {thread_id}: {e}")
    finally:
        try:
            await websocket.close()
        except:
            pass