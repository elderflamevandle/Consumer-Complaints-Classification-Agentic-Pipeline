"""Run FinComplaint pipeline + Legal Knowledge MCP requests (dev helper).

Usage examples (PowerShell, from repo root):
  python legal_knowledge_mcp/run_workflow.py --state NY
  python legal_knowledge_mcp/run_workflow.py --state CA --complaint-text "I was charged twice..."
  python legal_knowledge_mcp/run_workflow.py --mcp-only
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env")
except ImportError:
    pass


def _jsonable(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()  # pydantic v1 fallback
    return str(value)


def run_mcp_requests(requests_path: Path) -> list[dict[str, Any]]:
    from legal_knowledge_mcp.server import handle_request

    if not requests_path.exists():
        raise FileNotFoundError(f"request file not found: {requests_path}")
    payload = json.loads(requests_path.read_text(encoding="utf-8") or "[]")
    if isinstance(payload, dict):
        payload = [payload]
    if not isinstance(payload, list):
        raise ValueError("request.json must be a JSON object or array of objects")

    outputs: list[dict[str, Any]] = []
    for idx, item in enumerate(payload, start=1):
        if not isinstance(item, dict):
            outputs.append({"status": "error", "error": f"invalid_request_item:{idx}"})
            continue
        out = handle_request(item)
        outputs.append(out)
    return outputs


def run_pipeline(*, complaint_text: str, state_code: str) -> dict[str, Any]:
    from src.graph.pipeline import build_graph, run_complaint

    graph = build_graph()
    final_state = run_complaint(graph, complaint_text=complaint_text, state_code=state_code)
    return _jsonable(final_state)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run pipeline + MCP requests and print full output JSON.")
    parser.add_argument("--state", default="NY", help="2-letter state code for pipeline + MCP requests")
    parser.add_argument(
        "--complaint-text",
        default=(
            "Someone stole my identity last week, opened a checking account using my name, "
            "and started transferring money out of my real account."
        ),
        help="Complaint text to run through the pipeline",
    )
    parser.add_argument("--mcp-only", action="store_true", help="Only run MCP requests (skip pipeline).")
    parser.add_argument("--pipeline-only", action="store_true", help="Only run pipeline (skip MCP requests).")
    parser.add_argument(
        "--requests",
        default=str(Path("legal_knowledge_mcp") / "request.json"),
        help="Path to request.json (single request or array).",
    )
    args = parser.parse_args()

    state = str(args.state).strip().upper() or "NY"
    requests_path = (REPO_ROOT / args.requests).resolve()

    result: dict[str, Any] = {"state": state}

    if not args.mcp_only:
        result["pipeline"] = run_pipeline(complaint_text=str(args.complaint_text), state_code=state)

    if not args.pipeline_only:
        result["mcp_requests_path"] = str(requests_path)
        result["mcp"] = run_mcp_requests(requests_path)

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

