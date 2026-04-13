"""CLI MCP-style server: stdio or --request-json (used by MCPPolicyClient subprocess)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(_REPO_ROOT / '.env')
except ImportError:
    pass

from legal_knowledge_mcp.bridge import get_sla_requirements, search_state_regulations

TOOL_GET_SLA = 'get_sla_requirements'
TOOL_SEARCH = 'search_state_regulations'
TOOL_LIST = 'list_tools'


def handle_request(payload: dict[str, Any]) -> dict[str, Any]:
    tool = payload.get('tool')
    if tool == TOOL_LIST:
        return {'status': 'ok', 'result': [TOOL_GET_SLA, TOOL_SEARCH]}

    if tool == TOOL_SEARCH:
        arguments = payload.get('arguments', {})
        if not isinstance(arguments, dict):
            return {'status': 'error', 'error': 'arguments must be an object'}
        state = arguments.get('state')
        product_category = arguments.get('product_category')
        issue_code = arguments.get('issue_code')
        if not isinstance(state, str) or not isinstance(issue_code, str):
            return {'status': 'error', 'error': 'state and issue_code are required strings'}
        if not isinstance(product_category, str):
            product_category = ''
        try:
            result = search_state_regulations(
                state=state,
                product_category=product_category,
                issue_code=issue_code,
            )
        except Exception as error:
            return {'status': 'error', 'error': str(error)}
        return {'status': 'ok', 'result': result}

    if tool != TOOL_GET_SLA:
        return {'status': 'error', 'error': f'Unknown tool: {tool}'}

    arguments = payload.get('arguments', {})
    if not isinstance(arguments, dict):
        return {'status': 'error', 'error': 'arguments must be an object'}

    issue_type = arguments.get('issue_type')
    state_code = arguments.get('state_code')
    if not isinstance(issue_type, str) or not isinstance(state_code, str):
        return {'status': 'error', 'error': 'issue_type and state_code are required strings'}

    product_type = arguments.get('product_type')
    if product_type is not None and not isinstance(product_type, str):
        return {'status': 'error', 'error': 'product_type must be a string when provided'}

    path_raw = arguments.get('regulations_path')
    regulations_path: Path | None = None
    if isinstance(path_raw, str) and path_raw.strip():
        regulations_path = Path(path_raw)

    try:
        result = get_sla_requirements(
            issue_type=issue_type,
            state_code=state_code,
            product_type=product_type,
            regulations_path=regulations_path,
        )
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
    parser = argparse.ArgumentParser(description='Legal Knowledge Bridge MCP server')
    parser.add_argument('--tool')
    parser.add_argument('--issue-type')
    parser.add_argument('--state-code')
    parser.add_argument('--product-type')
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
        req: dict[str, Any] = {
            'tool': TOOL_GET_SLA,
            'arguments': {
                'issue_type': args.issue_type,
                'state_code': args.state_code,
            },
        }
        if args.product_type:
            req['arguments']['product_type'] = args.product_type
        print(json.dumps(handle_request(req)))
        return 0

    print(json.dumps({'status': 'ok', 'result': [TOOL_GET_SLA, TOOL_SEARCH]}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
