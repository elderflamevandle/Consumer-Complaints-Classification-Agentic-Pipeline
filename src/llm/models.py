"""Central model registry — loads all model assignments from config.yaml."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

_CONFIG_PATH = Path(__file__).parents[2] / "config.yaml"


@lru_cache(maxsize=1)
def _load_config() -> dict[str, Any]:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _models_cfg() -> dict[str, Any]:
    return _load_config()["models"]


# ---------------------------------------------------------------------------
# Public constants (kept for backwards-compat with existing imports)
# ---------------------------------------------------------------------------

@property  # type: ignore[misc]
def PRIMARY_MODEL() -> str:  # noqa: N802
    return _models_cfg()["fallback_chain"][0]


def _primary() -> str:
    return _models_cfg()["fallback_chain"][0]


def _fallback_chain() -> tuple[str, ...]:
    return tuple(_models_cfg()["fallback_chain"])


# Module-level names used by client.py
PRIMARY_MODEL: str = _primary()
SECONDARY_MODEL: str = _fallback_chain()[1] if len(_fallback_chain()) > 1 else _primary()
TERTIARY_MODEL: str = _fallback_chain()[2] if len(_fallback_chain()) > 2 else _primary()
FALLBACK_CHAIN: tuple[str, ...] = _fallback_chain()


def resolve_primary_model(agent_name: str) -> str:
    """Return the configured primary model for *agent_name*."""
    agents: dict[str, str] = _models_cfg().get("agents", {})
    return agents.get(agent_name, PRIMARY_MODEL)


def model_chain_for(agent_name: str, degrade_primary: bool = False) -> tuple[str, ...]:
    """Return the ordered model chain for *agent_name*.

    The agent's primary model leads, followed by the global fallback chain.
    Duplicate models are removed while preserving order.
    """
    preferred = resolve_primary_model(agent_name)
    chain = tuple(dict.fromkeys((preferred, *FALLBACK_CHAIN)))
    if degrade_primary and chain and chain[0] == PRIMARY_MODEL:
        return chain[1:] or chain
    return chain
