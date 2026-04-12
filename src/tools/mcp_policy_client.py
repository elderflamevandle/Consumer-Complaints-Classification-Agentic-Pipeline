"""MCP policy client for SLA requirement lookups used by remediator."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from legal_knowledge_mcp.server import TOOL_GET_SLA

DEFAULT_SERVER_PATH = Path('legal_knowledge_mcp/server.py')


class SLAPolicy(BaseModel):
    model_config = ConfigDict(extra='ignore')

    issue_type: str = Field(min_length=1)
    state_code: str = Field(min_length=2, max_length=2)
    sla_window: str = Field(min_length=1)
    required_actions: list[str] = Field(min_length=1)
    regulatory_basis: str = Field(min_length=1)
    product_type: str | None = None
    legal_citations: list[dict[str, str]] = Field(default_factory=list)


class PolicyLookupResult(BaseModel):
    model_config = ConfigDict(extra='forbid')

    status: str
    policy: SLAPolicy | None = None
    error: str | None = None

    @property
    def available(self) -> bool:
        return self.status == 'ok' and self.policy is not None


class MCPPolicyClient:
    def __init__(
        self,
        *,
        server_path: Path = DEFAULT_SERVER_PATH,
        timeout_seconds: float = 45.0,
        request_runner: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    ) -> None:
        self.server_path = server_path
        self.timeout_seconds = timeout_seconds
        self._request_runner = request_runner
        self.last_error: str | None = None

    def get_sla_requirements(
        self,
        *,
        issue_type: str,
        state_code: str,
        product_type: str | None = None,
    ) -> PolicyLookupResult:
        arguments: dict[str, str] = {
            'issue_type': issue_type,
            'state_code': state_code,
        }
        if product_type:
            arguments['product_type'] = product_type
        response = self._invoke(
            {
                'tool': TOOL_GET_SLA,
                'arguments': arguments,
            }
        )

        status = response.get('status')
        if status != 'ok':
            error = str(response.get('error', 'POLICY_UNAVAILABLE'))
            self.last_error = error
            return PolicyLookupResult(status='POLICY_UNAVAILABLE', error=error)

        payload = response.get('result')
        if not isinstance(payload, dict):
            self.last_error = 'POLICY_UNAVAILABLE: invalid_result_payload'
            return PolicyLookupResult(
                status='POLICY_UNAVAILABLE',
                error='invalid_result_payload',
            )

        try:
            policy = SLAPolicy.model_validate(payload)
        except ValidationError as error:
            self.last_error = f'POLICY_UNAVAILABLE: {error}'
            return PolicyLookupResult(
                status='POLICY_UNAVAILABLE',
                error='invalid_required_policy_fields',
            )

        self.last_error = None
        return PolicyLookupResult(status='ok', policy=policy)

    def _invoke(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self._request_runner is not None:
            return self._request_runner(payload)

        if not self.server_path.exists():
            return {'status': 'error', 'error': f'server_not_found:{self.server_path}'}

        command = [
            sys.executable,
            str(self.server_path),
            '--request-json',
            json.dumps(payload),
        ]

        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                timeout=self.timeout_seconds,
            )
        except Exception as error:
            return {'status': 'error', 'error': f'subprocess_error:{error}'}

        stdout = completed.stdout.strip()
        if completed.returncode != 0:
            return {
                'status': 'error',
                'error': f'non_zero_exit:{completed.returncode}:{completed.stderr.strip()}',
            }
        if not stdout:
            return {'status': 'error', 'error': 'empty_response'}

        try:
            parsed = json.loads(stdout)
        except Exception as error:
            return {'status': 'error', 'error': f'invalid_json_response:{error}'}

        if not isinstance(parsed, dict):
            return {'status': 'error', 'error': 'invalid_response_shape'}
        return parsed

