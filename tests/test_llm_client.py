from __future__ import annotations

from typing import Any

import pytest

from scripts import smoke_groq
from src.llm.client import (
    GroqLLMClient,
    LLMTimeoutError,
    NonRetryableLLMError,
    RateLimitError,
)
from src.llm.models import FALLBACK_CHAIN
from src.llm.rate_limiter import TokenBudgetTracker


class ScriptedTransport:
    def __init__(self, outcomes: list[Any]) -> None:
        self._outcomes = outcomes
        self.calls: list[str] = []

    def __call__(self, **kwargs: Any) -> dict[str, Any]:
        model = kwargs['model']
        self.calls.append(model)
        if not self._outcomes:
            return {'content': 'ok', 'usage': {'total_tokens': 7}}

        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def test_registry_contains_required_fallback_order() -> None:
    assert FALLBACK_CHAIN == (
        'llama-3.3-70b-versatile',
        'mixtral-8x7b-32768',
        'llama-3.1-8b-instant',
    )


def test_retry_and_fallback() -> None:
    transport = ScriptedTransport(
        [RateLimitError('429') for _ in range(4)]
        + [{'content': 'fallback-success', 'usage': {'total_tokens': 13}}]
    )
    client = GroqLLMClient(
        transport=transport,
        max_retries=3,
        sleep_fn=lambda _: None,
    )

    response = client.complete(prompt='hello', agent_name='default', critical=True)

    assert response.model == 'mixtral-8x7b-32768'
    assert transport.calls.count('llama-3.3-70b-versatile') == 4
    assert response.text == 'fallback-success'


def test_timeout_fallback_path() -> None:
    transport = ScriptedTransport(
        [LLMTimeoutError('timeout') for _ in range(4)]
        + [{'content': 'timeout-fallback', 'usage': {'total_tokens': 11}}]
    )
    client = GroqLLMClient(transport=transport, max_retries=3, sleep_fn=lambda _: None)

    response = client.complete(prompt='hello', agent_name='default', critical=True)

    assert response.model == 'mixtral-8x7b-32768'
    assert response.attempts == 5


def test_non_retryable_error_bubbles_up() -> None:
    transport = ScriptedTransport([NonRetryableLLMError('bad request')])
    client = GroqLLMClient(transport=transport, sleep_fn=lambda _: None)

    with pytest.raises(NonRetryableLLMError):
        client.complete(prompt='hello', agent_name='default')


def test_budget_degrade_for_non_critical_primary_calls() -> None:
    tracker = TokenBudgetTracker(daily_budget=100, warning_ratio=0.5, degrade_ratio=0.6)
    tracker.record_usage(65)
    transport = ScriptedTransport([
        {'content': 'degraded-model', 'usage': {'total_tokens': 3}}
    ])
    client = GroqLLMClient(
        transport=transport,
        budget_tracker=tracker,
        sleep_fn=lambda _: None,
    )

    response = client.complete(prompt='hello', agent_name='default', critical=False)

    assert response.degraded is True
    assert transport.calls[0] == 'mixtral-8x7b-32768'


def test_smoke_script_handles_missing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv('GROQ_API_KEY', raising=False)
    assert smoke_groq.main() == 0


def test_critical_calls_do_not_degrade_when_budget_is_over_threshold() -> None:
    tracker = TokenBudgetTracker(daily_budget=100, warning_ratio=0.5, degrade_ratio=0.6)
    tracker.record_usage(65)
    transport = ScriptedTransport([
        {'content': 'primary-critical', 'usage': {'total_tokens': 5}}
    ])
    client = GroqLLMClient(
        transport=transport,
        budget_tracker=tracker,
        sleep_fn=lambda _: None,
    )

    response = client.complete(prompt='hello', agent_name='default', critical=True)

    assert response.degraded is False
    assert transport.calls[0] == 'llama-3.3-70b-versatile'
