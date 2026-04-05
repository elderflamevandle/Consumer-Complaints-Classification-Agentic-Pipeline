"""Simple token budget tracker used by the LLM reliability layer."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock


@dataclass(frozen=True)
class BudgetSnapshot:
    used_tokens: int
    daily_budget: int
    utilization: float
    warning: bool
    degrade_non_critical: bool


class TokenBudgetTracker:
    def __init__(
        self,
        daily_budget: int,
        warning_ratio: float = 0.8,
        degrade_ratio: float = 0.9,
    ) -> None:
        if daily_budget <= 0:
            raise ValueError('daily_budget must be positive')
        self.daily_budget = daily_budget
        self.warning_ratio = warning_ratio
        self.degrade_ratio = degrade_ratio
        self._used_tokens = 0
        self._lock = Lock()

    def record_usage(self, tokens: int) -> None:
        if tokens <= 0:
            return
        with self._lock:
            self._used_tokens += tokens

    def snapshot(self) -> BudgetSnapshot:
        with self._lock:
            used_tokens = self._used_tokens
        utilization = used_tokens / self.daily_budget
        return BudgetSnapshot(
            used_tokens=used_tokens,
            daily_budget=self.daily_budget,
            utilization=utilization,
            warning=utilization >= self.warning_ratio,
            degrade_non_critical=utilization >= self.degrade_ratio,
        )

    def should_degrade_non_critical(self, *, critical: bool) -> bool:
        if critical:
            return False
        return self.snapshot().degrade_non_critical