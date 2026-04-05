"""Central model registry and deterministic fallback policy."""

from __future__ import annotations

from typing import Final

PRIMARY_MODEL: Final[str] = 'llama-3.3-70b-versatile'
SECONDARY_MODEL: Final[str] = 'mixtral-8x7b-32768'
TERTIARY_MODEL: Final[str] = 'llama-3.1-8b-instant'

FALLBACK_CHAIN: Final[tuple[str, str, str]] = (
    PRIMARY_MODEL,
    SECONDARY_MODEL,
    TERTIARY_MODEL,
)

AGENT_MODELS: Final[dict[str, str]] = {
    'classifier': PRIMARY_MODEL,
    'root_cause': PRIMARY_MODEL,
    'remediator': PRIMARY_MODEL,
    'writer': PRIMARY_MODEL,
    'auditor': PRIMARY_MODEL,
    'explainer': PRIMARY_MODEL,
    'default': PRIMARY_MODEL,
}


def resolve_primary_model(agent_name: str) -> str:
    return AGENT_MODELS.get(agent_name, PRIMARY_MODEL)


def model_chain_for(agent_name: str, degrade_primary: bool = False) -> tuple[str, ...]:
    preferred = resolve_primary_model(agent_name)
    chain = tuple(dict.fromkeys((preferred, *FALLBACK_CHAIN)))
    if degrade_primary and chain and chain[0] == PRIMARY_MODEL:
        return chain[1:] or chain
    return chain