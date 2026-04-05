"""Optional live Groq smoke check for Phase 1 reliability validation."""

from __future__ import annotations

from src.config import get_settings
from src.llm.client import GroqLLMClient, LLMClientError


def main() -> int:
    settings = get_settings()
    if not settings.groq_api_key:
        print('Skipping live Groq smoke check: GROQ_API_KEY is not set.')
        return 0

    client = GroqLLMClient()
    try:
        response = client.complete(
            prompt='Return a compact JSON object with key status set to ok.',
            agent_name='default',
            critical=False,
            max_tokens=64,
        )
    except LLMClientError as error:
        print(f'Groq smoke check failed: {error}')
        return 1

    print(f'Model: {response.model}')
    print(f'Attempts: {response.attempts}')
    print(f'Response: {response.text[:120]}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())