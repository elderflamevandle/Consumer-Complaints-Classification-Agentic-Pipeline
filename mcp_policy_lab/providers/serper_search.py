from __future__ import annotations

from mcp_policy_lab.http_utils import post_json
from mcp_policy_lab.policy_models import PolicyEvidence, PolicyProvider, PolicyRequest, PolicyResult


class SerperSearchProvider(PolicyProvider):
    name = "serper_search"

    def __init__(self, *, url: str, api_key: str, timeout_seconds: float = 20.0) -> None:
        self.url = url
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def resolve(self, request: PolicyRequest) -> PolicyResult | None:
        if not self.api_key:
            return None

        query = (
            f"{request.state_code} {request.issue_type} law regulation timeline site:gov "
            "site:ecfr.gov OR site:federalregister.gov OR site:regulations.gov"
        )
        payload = post_json(
            self.url,
            body={"q": query, "num": 5},
            headers={"X-API-KEY": self.api_key},
            timeout_seconds=self.timeout_seconds,
        )
        organic = payload.get("organic")
        if not isinstance(organic, list) or not organic:
            return None

        first = organic[0]
        if not isinstance(first, dict):
            return None

        title = str(first.get("title") or "Serper search result")
        url = str(first.get("link") or "")
        snippet = str(first.get("snippet") or "")
        if not url:
            return None

        return PolicyResult(
            status="ok",
            source=self.name,
            issue_type=request.issue_type,
            state_code=request.state_code.strip().upper(),
            sla_window="Search-discovered; verify from primary source text",
            required_actions=[
                "Open primary source",
                "Verify effective date and jurisdiction",
                "Extract enforceable obligations only",
            ],
            regulatory_basis=title,
            confidence=0.35,
            evidence=[PolicyEvidence(title=title, url=url, excerpt=snippet)],
            raw_payload=payload,
        )

