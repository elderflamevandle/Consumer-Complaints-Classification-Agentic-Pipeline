"""
Pydantic models for API request/response schemas.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime

class ComplaintRequest(BaseModel):
    """Request model for submitting a complaint."""
    complaint_text: str = Field(..., min_length=10, description="The complaint text")
    demo_id: Optional[str] = Field(None, description="Optional demo ID to load")

class ComplaintResponse(BaseModel):
    """Response model for complaint submission."""
    thread_id: str = Field(..., description="Unique thread identifier")
    status: str = Field(..., description="Initial status")
    created_at: str = Field(..., description="Creation timestamp")
    websocket_url: str = Field(..., description="WebSocket URL for live updates")

class StageInfo(BaseModel):
    """Model for pipeline stage information."""
    status: str
    model: Optional[str] = None
    latency_ms: int = 0
    tokens_used: int = 0
    output: Optional[Dict[str, Any]] = None

class ReviewState(BaseModel):
    """Model for review state."""
    reason: str
    interrupt_reason: str
    options: List[str]

class StatusResponse(BaseModel):
    """Response model for complaint status."""
    thread_id: str
    complaint_source: str
    current_stage: str
    status: str
    stages: Dict[str, StageInfo]
    review_state: Optional[ReviewState] = None
    response_draft: Optional[str] = None
    explanation: Optional[str] = None
    updated_at: str

class ReviewRequest(BaseModel):
    """Request model for review actions."""
    action: str = Field(..., pattern="^(approve|edit|reject)$", description="Review action")
    edit_text: Optional[str] = Field(None, description="Edited text for edit action")

class ReviewResponse(BaseModel):
    """Response model for review submission."""
    thread_id: str
    status: str
    message: str
    updated_at: str

class AuditEvent(BaseModel):
    """Model for audit events."""
    timestamp: str
    sequence: int
    node: str
    operation: str
    model: Optional[str] = None
    latency_ms: int = 0
    tokens_used: int = 0
    decision: str

class AuditResponse(BaseModel):
    """Response model for audit events."""
    thread_id: str
    events: List[AuditEvent]
    total_events: int

class BudgetResponse(BaseModel):
    """Response model for token budget."""
    daily_limit: int
    used_today: int
    remaining: int
    percent_used: float
    warning_threshold: float
    degradation_threshold: float
    status: str
    reset_at: str

class DemoItem(BaseModel):
    """Model for golden demo items."""
    demo_id: str
    title: str
    summary: str
    category: str
    complaint_text: str

class DemosResponse(BaseModel):
    """Response model for golden demos."""
    demos: List[DemoItem]

class ErrorResponse(BaseModel):
    """Model for error responses."""
    detail: str