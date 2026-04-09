from __future__ import annotations

from typing import Any

from mcp_policy_lab.http_utils import post_json
from mcp_policy_lab.policy_models import PolicyEvidence, PolicyProvider, PolicyRequest, PolicyResult


class GovInfoMCPProvider(PolicyProvider):
    """Minimal MCP tools/call wrapper for GovInfo MCP.

    This implementation assumes a JSON-RPC style tools/call request.
    Some MCP clients/transports may require session negotiation; treat this as
    a practical starter, not a full transport implementation.
    """

    name = "govinfo_mcp"

    def __init__(self, *, mcp_url: str, api_key: str, timeout_seconds: float = 20.0) -> None:
        self.mcp_url = mcp_url
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def resolve(self, request: PolicyRequest) -> PolicyResult | None:
        if not self.api_key:
            return None

        query = (
            f"{request.state_code} {request.issue_type} complaint handling timeline "
            "regulation statute official guidance"
        )
        payload = self._tool_call(
            tool_name="searchGovInfo",
            arguments={"query": query},
        )
        items = _extract_items(payload)
        if not items:
            return None

        top = items[0]
        title = str(top.get("title") or "GovInfo result")
        url = str(top.get("url") or top.get("link") or "https://www.govinfo.gov/")
        excerpt = str(top.get("snippet") or top.get("teaser") or "")

        return PolicyResult(
            status="ok",
            source=self.name,
            issue_type=request.issue_type,
            state_code=request.state_code.strip().upper(),
            sla_window="Needs extraction from cited text",
            required_actions=[
                "Review cited federal publication text",
                "Map to complaint issue and jurisdiction",
                "Extract enforceable deadlines and obligations",
            ],
            regulatory_basis=title,
            confidence=0.65,
            evidence=[PolicyEvidence(title=title, url=url, excerpt=excerpt)],
            raw_payload=payload,
        )

    def _tool_call(self, *, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        headers = {"x-api-key": self.api_key}
        body = {
            "jsonrpc": "2.0",
            "id": "policy-lab-1",
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }
        return post_json(
            self.mcp_url,
            body=body,
            headers=headers,
            timeout_seconds=self.timeout_seconds,
        )


def _extract_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    result = payload.get("result")
    if isinstance(result, dict):
        for key in ("items", "results", "data"):
            candidate = result.get(key)
            if isinstance(candidate, list):
                return [item for item in candidate if isinstance(item, dict)]
    if isinstance(result, list):
        return [item for item in result if isinstance(item, dict)]
    return []

