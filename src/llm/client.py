"""Groq client wrapper with deterministic retry, timeout, fallback, and budget degrade."""

from __future__ import annotations

from dataclasses import dataclass
from time import sleep as default_sleep
from typing import Any, Callable, Mapping, Sequence, cast

from src.config import get_settings
from src.llm.models import FALLBACK_CHAIN, model_chain_for, resolve_primary_model
from src.llm.rate_limiter import TokenBudgetTracker

MessageList = Sequence[Mapping[str, str]]
TransportCallable = Callable[..., Mapping[str, Any]]


class LLMClientError(RuntimeError):
    """Base class for deterministic LLM policy failures."""


class RateLimitError(LLMClientError):
    pass


class LLMTimeoutError(LLMClientError):
    pass


class TransientServerError(LLMClientError):
    pass


class NonRetryableLLMError(LLMClientError):
    pass


class RetryExhaustedError(LLMClientError):
    pass


@dataclass(frozen=True)
class LLMResponse:
    text: str
    model: str
    total_tokens: int
    attempts: int
    degraded: bool


def _extract_text(payload: Mapping[str, Any]) -> str:
    content = payload.get('content')
    if isinstance(content, str):
        return content

    choices = payload.get('choices')
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, Mapping):
            message = first.get('message')
            if isinstance(message, Mapping):
                text = message.get('content')
                if isinstance(text, str):
                    return text
    return ''


def _extract_total_tokens(payload: Mapping[str, Any]) -> int:
    usage = payload.get('usage')
    if isinstance(usage, Mapping):
        tokens = usage.get('total_tokens', 0)
        if isinstance(tokens, int):
            return max(tokens, 0)
    return 0


def _normalize_error(error: Exception) -> Exception:
    retryable_types = (
        RateLimitError,
        LLMTimeoutError,
        TransientServerError,
        NonRetryableLLMError,
    )
    if isinstance(error, retryable_types):
        return error

    if isinstance(error, TimeoutError):
        return LLMTimeoutError(str(error))

    status_code = getattr(error, 'status_code', None)
    if status_code == 429:
        return RateLimitError(str(error))
    if isinstance(status_code, int) and 500 <= status_code < 600:
        return TransientServerError(str(error))

    return NonRetryableLLMError(str(error))


class GroqLLMClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
        max_retries: int | None = None,
        backoff_base_seconds: float | None = None,
        backoff_max_seconds: float | None = None,
        transport: TransportCallable | None = None,
        sleep_fn: Callable[[float], None] = default_sleep,
        budget_tracker: TokenBudgetTracker | None = None,
    ) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.groq_api_key
        self.base_url = base_url or settings.groq_base_url
        self.timeout_seconds = timeout_seconds or settings.request_timeout_seconds
        self.max_retries = max_retries if max_retries is not None else settings.max_retries
        self.backoff_base_seconds = (
            backoff_base_seconds
            if backoff_base_seconds is not None
            else settings.backoff_base_seconds
        )
        self.backoff_max_seconds = (
            backoff_max_seconds
            if backoff_max_seconds is not None
            else settings.backoff_max_seconds
        )
        self._sleep = sleep_fn
        self._budget = budget_tracker or TokenBudgetTracker(settings.daily_token_budget)
        self._transport = transport or self._openai_compatible_transport

    def complete(
        self,
        *,
        prompt: str,
        agent_name: str = 'default',
        system_prompt: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 512,
        critical: bool = True,
    ) -> LLMResponse:
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({'role': 'system', 'content': system_prompt})
        messages.append({'role': 'user', 'content': prompt})

        degraded = self._budget.should_degrade_non_critical(critical=critical)
        chain = model_chain_for(agent_name, degrade_primary=degraded)
        if not chain:
            chain = FALLBACK_CHAIN

        attempts = 0
        for model in chain:
            for attempt in range(self.max_retries + 1):
                attempts += 1
                try:
                    payload = self._transport(
                        model=model,
                        messages=messages,
                        timeout=self.timeout_seconds,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                    text = _extract_text(payload)
                    total_tokens = _extract_total_tokens(payload)
                    self._budget.record_usage(total_tokens)
                    return LLMResponse(
                        text=text,
                        model=model,
                        total_tokens=total_tokens,
                        attempts=attempts,
                        degraded=degraded,
                    )
                except Exception as raw_error:
                    normalized = _normalize_error(raw_error)
                    retryable = isinstance(
                        normalized,
                        (RateLimitError, LLMTimeoutError, TransientServerError),
                    )
                    if not retryable:
                        raise normalized from raw_error
                    if attempt == self.max_retries:
                        break
                    self._sleep(self._backoff_seconds(attempt))

        chain_text = ' -> '.join(chain)
        raise RetryExhaustedError(
            f'All retries exhausted across fallback chain: {chain_text}'
        )

    def _backoff_seconds(self, attempt: int) -> float:
        duration = self.backoff_base_seconds * (2 ** attempt)
        return min(duration, self.backoff_max_seconds)

    def _openai_compatible_transport(
        self,
        *,
        model: str,
        messages: MessageList,
        timeout: float,
        temperature: float,
        max_tokens: int,
    ) -> Mapping[str, Any]:
        if not self.api_key:
            raise NonRetryableLLMError('GROQ_API_KEY is required for live calls')

        try:
            from openai import OpenAI
        except Exception as import_error:
            raise NonRetryableLLMError(
                'openai package is required for live calls'
            ) from import_error

        client = OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=timeout)
        typed_messages = cast(Any, [dict(m) for m in messages])
        try:
            response = client.chat.completions.create(
                model=model,
                messages=typed_messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as api_error:
            normalized = _normalize_error(api_error)
            raise normalized from api_error

        content = ''
        if response.choices and response.choices[0].message:
            content = response.choices[0].message.content or ''
        total_tokens = int(response.usage.total_tokens or 0) if response.usage else 0
        return {'content': content, 'usage': {'total_tokens': total_tokens}}


def default_degrade_target(agent_name: str) -> str:
    """Expose deterministic degraded model selection for telemetry/tests."""
    chain = model_chain_for(agent_name, degrade_primary=True)
    return chain[0] if chain else resolve_primary_model(agent_name)