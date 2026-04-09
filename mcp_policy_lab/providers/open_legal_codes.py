from __future__ import annotations

from mcp_policy_lab.http_utils import get_json
from mcp_policy_lab.policy_models import PolicyEvidence, PolicyProvider, PolicyRequest, PolicyResult


class OpenLegalCodesProvider(PolicyProvider):
    name = "open_legal_codes"

    def __init__(self, *, base_url: str, timeout_seconds: float = 20.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def resolve(self, request: PolicyRequest) -> PolicyResult | None:
        issue_query = _issue_to_query(request.issue_type)
        response = get_json(
            f"{self.base_url}/search",
            query={"q": issue_query, "state": request.state_code.strip().upper()},
            timeout_seconds=self.timeout_seconds,
        )
        items = _extract_items(response)
        if not items:
            return None

        best = items[0]
        title = str(best.get("title") or "Open Legal Codes search result")
        url = str(best.get("url") or best.get("permalink") or "https://openlegalcodes.org/")
        excerpt = str(best.get("snippet") or best.get("text") or "")

        return PolicyResult(
            status="ok",
            source=self.name,
            issue_type=request.issue_type,
            state_code=request.state_code.strip().upper(),
            sla_window="Extract from matched statute text",
            required_actions=[
                "Read matched code section",
                "Extract deadlines and mandatory notices",
                "Attach statute permalink in response",
            ],
            regulatory_basis=title,
            confidence=0.6,
            evidence=[PolicyEvidence(title=title, url=url, excerpt=excerpt)],
            raw_payload=response,
        )


def _issue_to_query(issue_type: str) -> str:
    text = issue_type.strip()
    lowered = text.lower()
    if "fraud" in lowered:
        return "fraud unauthorized transaction notice deadline"
    if "fee" in lowered or "interest" in lowered:
        return "fee dispute billing error timeline"
    if "credit" in lowered and "report" in lowered:
        return "credit report dispute reinvestigation timeline"
    return text


def _extract_items(response: dict[str, object]) -> list[dict[str, object]]:
    for key in ("items", "results", "data"):
        raw = response.get(key)
        if isinstance(raw, list):
            return [item for item in raw if isinstance(item, dict)]
        if isinstance(raw, dict):
            nested = raw.get("items")
            if isinstance(nested, list):
                return [item for item in nested if isinstance(item, dict)]
    return []

