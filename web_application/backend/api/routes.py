"""
FastAPI routes for the complaint API.
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
import logging

from .schemas import (
    ComplaintRequest, ComplaintResponse, StatusResponse,
    ReviewRequest, ReviewResponse, AuditResponse, BudgetResponse, DemosResponse
)
from ..core.orchestrator import ComplaintOrchestrator
from ..services.rate_limiter import RateLimiter
from ..services.budget_service import BudgetService

logger = logging.getLogger(__name__)

router = APIRouter()
orchestrator = ComplaintOrchestrator()
rate_limiter = RateLimiter()
budget_service = BudgetService()

@router.post("/complaints", response_model=ComplaintResponse)
async def submit_complaint(
    request: ComplaintRequest,
    req: Request
) -> ComplaintResponse:
    """Submit a new complaint for processing."""
    # Rate limiting
    client_ip = req.client.host if req.client else "unknown"
    if not rate_limiter.allow(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    try:
        thread_id = await orchestrator.submit_complaint(
            request.complaint_text,
            request.demo_id
        )

        websocket_url = f"ws://{req.headers.get('host', 'localhost:8000')}/ws/complaints/{thread_id}"

        return ComplaintResponse(
            thread_id=thread_id,
            status="pending",
            created_at="now",  # Would use datetime.utcnow().isoformat()
            websocket_url=websocket_url
        )
    except Exception as e:
        logger.error(f"Error submitting complaint: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit complaint")

@router.get("/complaints/{thread_id}", response_model=StatusResponse)
async def get_complaint_status(thread_id: str) -> StatusResponse:
    """Get the current status of a complaint thread."""
    try:
        status = await orchestrator.get_status(thread_id)
        return StatusResponse(**status)
    except ValueError:
        raise HTTPException(status_code=404, detail="Thread not found")
    except Exception as e:
        logger.error(f"Error getting status for thread {thread_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get status")

@router.post("/complaints/{thread_id}/review", response_model=ReviewResponse)
async def submit_review(
    thread_id: str,
    request: ReviewRequest
) -> ReviewResponse:
    """Submit a review action for a complaint thread."""
    try:
        result = await orchestrator.submit_review_action(
            thread_id,
            request.action,
            request.edit_text
        )
        return ReviewResponse(
            thread_id=thread_id,
            status=result["status"],
            message="Review action submitted. Pipeline resuming...",
            updated_at=result["updated_at"]
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="Thread not found")
    except Exception as e:
        logger.error(f"Error submitting review for thread {thread_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit review")

@router.get("/complaints/{thread_id}/audit", response_model=AuditResponse)
async def get_audit_events(thread_id: str) -> AuditResponse:
    """Get audit events for a complaint thread."""
    try:
        audit = await orchestrator.get_audit_events(thread_id)
        return AuditResponse(**audit)
    except ValueError:
        raise HTTPException(status_code=404, detail="Thread not found")
    except Exception as e:
        logger.error(f"Error getting audit for thread {thread_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get audit events")

@router.get("/budget", response_model=BudgetResponse)
async def get_budget_status() -> BudgetResponse:
    """Get current token budget status."""
    try:
        budget = budget_service.get_budget_status()
        return BudgetResponse(**budget)
    except Exception as e:
        logger.error(f"Error getting budget status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get budget status")

@router.get("/demos", response_model=DemosResponse)
async def get_golden_demos() -> DemosResponse:
    """Get list of golden demo complaints."""
    # For now, return hardcoded demos
    # In production, this would load from a config file or database
    demos = [
        {
            "demo_id": "demo_001_billing_dispute",
            "title": "Billing Error on Credit Card",
            "summary": "Customer was charged twice for same purchase",
            "category": "billing_error",
            "complaint_text": "I made a purchase on April 5th for $150..."
        },
        {
            "demo_id": "demo_002_unauthorized_transaction",
            "title": "Unauthorized Transaction",
            "summary": "Customer reports fraudulent charges they did not authorize",
            "category": "fraud",
            "complaint_text": "I noticed charges on my account..."
        }
    ]
    return DemosResponse(demos=demos)