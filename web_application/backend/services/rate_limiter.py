"""
Rate limiting service for API requests.
"""

from collections import defaultdict
import time
from typing import Dict

class RateLimiter:
    """Simple in-memory rate limiter."""

    def __init__(self):
        self.requests: Dict[str, list] = defaultdict(list)
        self.max_requests = 100  # per hour
        self.window_seconds = 3600  # 1 hour

    def allow(self, client_ip: str) -> bool:
        """Check if request is allowed for the given IP."""
        now = time.time()
        self.requests[client_ip] = [
            timestamp for timestamp in self.requests[client_ip]
            if now - timestamp < self.window_seconds
        ]

        if len(self.requests[client_ip]) >= self.max_requests:
            return False

        self.requests[client_ip].append(now)
        return True