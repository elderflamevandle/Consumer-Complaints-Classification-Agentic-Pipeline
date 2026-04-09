"""Local MCP-style policy server for SLA requirement lookups."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

TOOL_GET_SLA = 'get_sla_requirements'
TOOL_LIST = 'list_tools'
REQUIRED_POLICY_FIELDS = ('sla_window', 'required_actions', 'regulatory_basis')
DEFAULT_REGULATIONS_PATH = Path(__file__).with_name('mock_regulations.json')


def _normalize_issue(issue_type: str) -> str:
    normalized = issue_type.strip().upper()
    normalized = re.sub(r'[\s\-]+', '_', normalized)   # spaces/hyphens → underscore
    normalized = re.sub(r'[^A-Z0-9_]', '', normalized) # remove all other non-word chars
    return normalized


def _load_regulations(path: Path = DEFAULT_REGULATIONS_PATH) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(payload, dict):
        raise ValueError('Regulations file must contain a JSON object')
    return payload


def _validate_policy_fields(policy: dict[str, Any]) -> dict[str, Any]:
    for key in REQUIRED_POLICY_FIELDS:
        if key not in policy:
            raise ValueError(f'Policy missing required field: {key}')
    if not isinstance(policy['required_actions'], list):
        raise ValueError('required_actions must be a list')
    return policy


def get_sla_requirements(
    *,
    issue_type: str,
    state_code: str,
    regulations_path: Path = DEFAULT_REGULATIONS_PATH,
) -> dict[str, Any]:
    regulations = _load_regulations(regulations_path)
    default_policy = regulations.get('default')
    if not isinstance(default_policy, dict):
        raise ValueError('Regulations default policy is invalid')

    issue_key = _normalize_issue(issue_type)
    state_key = state_code.strip().upper()

    issue_policy = regulations.get('issues', {})
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

    if selected is None:
        selected = default_policy

    policy = _validate_policy_fields(dict(selected))
    return {
        'issue_type': issue_key,
        'state_code': state_key,
        'sla_window': str(policy['sla_window']),
        'required_actions': [str(item) for item in policy['required_actions']],
        'regulatory_basis': str(policy['regulatory_basis']),
    }


def handle_request(payload: dict[str, Any]) -> dict[str, Any]:
    tool = payload.get('tool')
    if tool == TOOL_LIST:
        return {'status': 'ok', 'result': [TOOL_GET_SLA]}

    if tool != TOOL_GET_SLA:
        return {'status': 'error', 'error': f'Unknown tool: {tool}'}

    arguments = payload.get('arguments', {})
    if not isinstance(arguments, dict):
        return {'status': 'error', 'error': 'arguments must be an object'}

    issue_type = arguments.get('issue_type')
    state_code = arguments.get('state_code')
    if not isinstance(issue_type, str) or not isinstance(state_code, str):
        return {'status': 'error', 'error': 'issue_type and state_code are required strings'}

    try:
        result = get_sla_requirements(issue_type=issue_type, state_code=state_code)
    except Exception as error:
        return {'status': 'error', 'error': str(error)}

    return {'status': 'ok', 'result': result}


def _stdio_loop() -> int:
    for line in sys.stdin:
        text = line.strip()
        if not text:
            continue

        try:
            payload = json.loads(text)
            if not isinstance(payload, dict):
                raise ValueError('request payload must be an object')
        except Exception as error:
            response = {'status': 'error', 'error': f'invalid_request: {error}'}
            print(json.dumps(response), flush=True)
            continue

        response = handle_request(payload)
        print(json.dumps(response), flush=True)

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description='Local MCP policy server')
    parser.add_argument('--tool')
    parser.add_argument('--issue-type')
    parser.add_argument('--state-code')
    parser.add_argument('--request-json')
    parser.add_argument('--stdio', action='store_true')
    args = parser.parse_args()

    if args.stdio:
        return _stdio_loop()

    if args.request_json:
        payload = json.loads(args.request_json)
        if not isinstance(payload, dict):
            raise ValueError('request-json must decode to an object')
        print(json.dumps(handle_request(payload)))
        return 0

    if args.tool == TOOL_GET_SLA:
        if not args.issue_type or not args.state_code:
            raise ValueError('--issue-type and --state-code are required for get_sla_requirements')
        response = handle_request(
            {
                'tool': TOOL_GET_SLA,
                'arguments': {
                    'issue_type': args.issue_type,
                    'state_code': args.state_code,
                },
            }
        )
        print(json.dumps(response))
        return 0

    print(json.dumps({'status': 'ok', 'result': [TOOL_GET_SLA]}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

