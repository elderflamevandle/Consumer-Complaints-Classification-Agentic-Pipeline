"""Load and select SLA policy rows from the shared regulations JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from legal_knowledge_mcp.normalize import normalize_issue

REQUIRED_POLICY_FIELDS = ('sla_window', 'required_actions', 'regulatory_basis')
FALLBACK_POLICY: dict[str, Any] = {
    'sla_window': '30 calendar days',
    'required_actions': [
        'Acknowledge complaint receipt',
        'Open internal case and assign owner',
        'Provide written resolution summary',
    ],
    'regulatory_basis': 'CFPB complaint response baseline guidance',
}


def regulations_path_default() -> Path:
    """Regulations file lives alongside the legacy mcp_server package."""
    return Path(__file__).resolve().parent.parent / 'mcp_server' / 'mock_regulations.json'


def load_regulations(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(payload, dict):
        raise ValueError('Regulations file must contain a JSON object')
    return payload


def validate_policy_fields(policy: dict[str, Any]) -> dict[str, Any]:
    for key in REQUIRED_POLICY_FIELDS:
        if key not in policy:
            raise ValueError(f'Policy missing required field: {key}')
    if not isinstance(policy['required_actions'], list):
        raise ValueError('required_actions must be a list')
    return policy


def select_policy(*, regulations: dict[str, Any], issue_key: str, state_key: str) -> dict[str, Any]:
    default_policy = regulations.get('default')
    issue_policy = regulations.get('issues')
    if isinstance(default_policy, dict) and isinstance(issue_policy, dict):
        selected = _select_legacy_policy(
            issue_policy=issue_policy,
            issue_key=issue_key,
            state_key=state_key,
        )
        if isinstance(selected, dict):
            return selected
        return dict(default_policy)

    generated = _select_generated_policy(
        regulations=regulations,
        issue_key=issue_key,
        state_key=state_key,
    )
    if isinstance(generated, dict):
        return generated

    return dict(FALLBACK_POLICY)


def _select_legacy_policy(
    *,
    issue_policy: dict[str, Any],
    issue_key: str,
    state_key: str,
) -> dict[str, Any] | None:
    issue_block = issue_policy.get(issue_key, {}) if isinstance(issue_policy, dict) else {}
    selected: dict[str, Any] | None = None
    if isinstance(issue_block, dict):
        states = issue_block.get('states')
        if isinstance(states, dict):
            state_policy = states.get(state_key)
            if isinstance(state_policy, dict):
                selected = state_policy

        if selected is None:
            issue_default = issue_block.get('default')
            if isinstance(issue_default, dict):
                selected = issue_default
    return selected


def _select_generated_policy(
    *,
    regulations: dict[str, Any],
    issue_key: str,
    state_key: str,
) -> dict[str, Any] | None:
    issue_norms = regulations.get('issue_norms')
    state_defaults = regulations.get('state_defaults')
    state_overrides = regulations.get('state_overrides')

    if not isinstance(issue_norms, dict):
        return None

    base = issue_norms.get(issue_key)
    selected: dict[str, Any] = dict(base) if isinstance(base, dict) else {}

    if not selected and isinstance(state_defaults, dict):
        state_default = state_defaults.get(state_key)
        if isinstance(state_default, dict):
            selected = dict(state_default)

    if isinstance(state_overrides, dict):
        state_block = state_overrides.get(state_key)
        if isinstance(state_block, dict):
            default_override = state_block.get('default')
            if isinstance(default_override, dict):
                selected.update(default_override)
            issue_block = state_block.get('issues')
            if isinstance(issue_block, dict):
                issue_override = issue_block.get(issue_key)
                if isinstance(issue_override, dict):
                    selected.update(issue_override)

    return selected or None


def build_base_policy(
    *,
    issue_type: str,
    state_code: str,
    regulations_path: Path | None = None,
) -> dict[str, Any]:
    path = regulations_path or regulations_path_default()
    regulations = load_regulations(path)
    issue_key = normalize_issue(issue_type)
    state_key = state_code.strip().upper()
    selected = select_policy(regulations=regulations, issue_key=issue_key, state_key=state_key)
    policy = validate_policy_fields(dict(selected))
    return {
        'issue_type': issue_key,
        'state_code': state_key,
        'sla_window': str(policy['sla_window']),
        'required_actions': [str(item) for item in policy['required_actions']],
        'regulatory_basis': str(policy['regulatory_basis']),
    }
