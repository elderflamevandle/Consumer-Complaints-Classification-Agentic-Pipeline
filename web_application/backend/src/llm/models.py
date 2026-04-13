"""Central model registry and deterministic fallback policy."""

from __future__ import annotations

from typing import Final

PRIMARY_MODEL: Final[str] = "llama-3.3-70b-versatile"
SECONDARY_MODEL: Final[str] = "qwen/qwen3-32b"
TERTIARY_MODEL: Final[str] = "llama-3.1-8b-instant"

FALLBACK_CHAIN: Final[tuple[str, str, str]] = (
    PRIMARY_MODEL,
    SECONDARY_MODEL,
    TERTIARY_MODEL,
)

AGENT_MODELS: Final[dict[str, str]] = {
    'classifier': "llama-3.3-70b-versatile",
    'root_cause': "qwen/qwen3-32b",
    'remediator': "qwen/qwen3-32b",
    'writer':     "llama-3.3-70b-versatile",
    'auditor':    "qwen/qwen3-32b",
    'explainer':  "llama-3.3-70b-versatile",
    'default':    "llama-3.1-8b-instant",
}


def resolve_primary_model(agent_name: str) -> str:
    return AGENT_MODELS.get(agent_name, PRIMARY_MODEL)


def model_chain_for(agent_name: str, degrade_primary: bool = False) -> tuple[str, ...]:
    preferred = resolve_primary_model(agent_name)
    chain = tuple(dict.fromkeys((preferred, *FALLBACK_CHAIN)))
    if degrade_primary and chain and chain[0] == PRIMARY_MODEL:
        return chain[1:] or chain
    return chain