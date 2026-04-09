"""
Service for tracking token budget usage.
"""

from datetime import datetime, timedelta
from typing import Dict, Any

class BudgetService:
    """Service for managing token budget tracking."""

    def __init__(self):
        self.daily_limit = 1000000  # 1M tokens per day
        self.warning_threshold = 0.80  # 80%
        self.degradation_threshold = 0.95  # 95%

    def get_budget_status(self) -> Dict[str, Any]:
        """Get current budget status."""
        # For now, return mock data
        # In production, this would integrate with actual token tracking
        used_today = 347821
        remaining = self.daily_limit - used_today
        percent_used = (used_today / self.daily_limit) * 100

        if percent_used >= self.degradation_threshold * 100:
            status = "degraded"
        elif percent_used >= self.warning_threshold * 100:
            status = "warning"
        else:
            status = "normal"

        reset_at = (datetime.utcnow() + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

        return {
            "daily_limit": self.daily_limit,
            "used_today": used_today,
            "remaining": remaining,
            "percent_used": percent_used,
            "warning_threshold": self.warning_threshold,
            "degradation_threshold": self.degradation_threshold,
            "status": status,
            "reset_at": reset_at.isoformat()
        }