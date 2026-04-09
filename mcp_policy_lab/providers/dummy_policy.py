from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mcp_policy_lab.policy_models import (
    PolicyEvidence,
    PolicyProvider,
    PolicyRequest,
    PolicyResult,
)


class DummyPolicyProvider(PolicyProvider):
    name = "dummy_local"

    def __init__(self, *, path: Path) -> None:
        self.path = path

    def resolve(self, request: PolicyRequest) -> PolicyResult | None:
        payload = self._read()
        issue_key = _normalize_issue(request.issue_type)
        state = request.state_code.strip().upper()
        issue_policy = self._resolve_policy(payload=payload, state=state, issue_key=issue_key)
        if issue_policy is None:
            return None

        actions = issue_policy.get("required_actions", [])
        if not isinstance(actions, list) or not actions:
            return None

        return PolicyResult(
            status="ok",
            source=self.name,
            issue_type=issue_key,
            state_code=state,
            sla_window=str(issue_policy.get("sla_window", "30 calendar days")),
            required_actions=[str(item) for item in actions],
            regulatory_basis=str(issue_policy.get("regulatory_basis", "Dummy local policy basis")),
            confidence=0.55,
            evidence=[
                PolicyEvidence(
                    title="dummy_policy_rules.json",
                    url=str(self.path),
                    excerpt="Local deterministic dummy policy match",
                )
            ],
            raw_payload={"issue_key": issue_key},
        )

    def _read(self) -> dict[str, Any]:
        raw = self.path.read_text(encoding="utf-8")
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise ValueError("Dummy policy file must be a JSON object")
        return parsed

    def _resolve_policy(
        self,
        *,
        payload: dict[str, Any],
        state: str,
        issue_key: str,
    ) -> dict[str, Any] | None:
        """Support both legacy state->issues shape and generated norms shape."""
        states = payload.get("states")
        if isinstance(states, dict):
            state_block = states.get(state)
            if isinstance(state_block, dict):
                issues = state_block.get("issues", {})
                issue_policy = issues.get(issue_key) if isinstance(issues, dict) else None
                if isinstance(issue_policy, dict):
                    return issue_policy
                default_policy = state_block.get("default")
                if isinstance(default_policy, dict):
                    return default_policy

        # Generated norms shape
        known_states = payload.get("state_codes")
        if isinstance(known_states, list) and state not in known_states:
            return None

        issue_norms = payload.get("issue_norms")
        state_defaults = payload.get("state_defaults")
        state_overrides = payload.get("state_overrides")
        if not isinstance(issue_norms, dict) or not isinstance(state_defaults, dict):
            return None

        base = issue_norms.get(issue_key)
        if not isinstance(base, dict):
            base = state_defaults.get(state)
            if not isinstance(base, dict):
                return None
            return dict(base)

        merged = dict(base)
        if isinstance(state_overrides, dict):
            block = state_overrides.get(state)
            if isinstance(block, dict):
                issue_block = block.get("issues")
                if isinstance(issue_block, dict):
                    candidate = issue_block.get(issue_key)
                    if isinstance(candidate, dict):
                        merged.update(candidate)
                default_block = block.get("default")
                if isinstance(default_block, dict):
                    # Fill only missing keys from state default override.
                    for key, value in default_block.items():
                        merged.setdefault(key, value)
        return merged


def _normalize_issue(issue_type: str) -> str:
    token = issue_type.strip().upper().replace("-", "_").replace(" ", "_")
    keep = []
    for ch in token:
        if ch.isalnum() or ch == "_":
            keep.append(ch)
    return "".join(keep)
