from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from mcp_policy_lab.resolver import build_default_resolver
from mcp_policy_lab.policy_models import PolicyRequest


def main() -> int:
    parser = argparse.ArgumentParser(description="Standalone MCP policy lab demo")
    parser.add_argument("--issue", required=True, help="Issue label, e.g. 'Fraud or scam'")
    parser.add_argument("--state", required=True, help="Two-letter state code, e.g. NY")
    parser.add_argument("--complaint", default="", help="Optional complaint text")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    resolver = build_default_resolver(root=root)
    output = resolver.resolve(
        PolicyRequest(
            issue_type=args.issue,
            state_code=args.state,
            complaint_text=args.complaint,
        )
    )

    print("=== Resolver Trace ===")
    for trace in output.traces:
        print(f"- {trace.provider}: {trace.message}")

    print("\n=== Result ===")
    if output.result is None:
        print("No policy result resolved")
        return 1

    print(json.dumps(asdict(output.result), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

