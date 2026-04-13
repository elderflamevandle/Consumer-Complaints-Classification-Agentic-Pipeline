"""Aggregate federal (GovInfo) + state (Open States) search into one ranked citation list."""

from __future__ import annotations

import os
from typing import Any

from legal_knowledge_mcp.extract import extract_timeframe_hint
from legal_knowledge_mcp.normalize import normalize_issue
from legal_knowledge_mcp.query_builder import govinfo_query, open_states_query
from legal_knowledge_mcp.sources.govinfo_client import fetch_govinfo_citations
from legal_knowledge_mcp.sources.open_states_client import fetch_open_states_bills


def use_mock_fallback() -> bool:
    v = (os.environ.get('LEGAL_MCP_USE_MOCK_FALLBACK') or '').strip().lower()
    return v in ('1', 'true', 'yes', 'on')


def api_keys_configured() -> bool:
    gov = (os.environ.get('GOVINFO_API_KEY') or os.environ.get('DATA_GOV_API_KEY') or '').strip()
    st = (os.environ.get('OPEN_STATES_API_KEY') or '').strip()
    return bool(gov or st)


def _tokenize(*parts: str | None) -> list[str]:
    out: list[str] = []
    for p in parts:
        if not p:
            continue
        for w in p.replace('_', ' ').lower().split():
            if len(w) > 2:
                out.append(w)
    return out


def _score(citation: dict[str, str], tokens: list[str]) -> int:
    blob = f"{citation.get('title', '')} {citation.get('excerpt', '')}".lower()
    return sum(1 for t in tokens if t in blob)


def rank_citations(
    citations: list[dict[str, str]],
    *,
    issue_type: str,
    product_token: str | None,
    state_code: str,
) -> list[dict[str, str]]:
    tokens = _tokenize(
        normalize_issue(issue_type),
        product_token,
        state_code,
        issue_type,
    )
    scored = [(_score(c, tokens), i, c) for i, c in enumerate(citations)]
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [c for _, __, c in scored]


def build_live_policy(
    *,
    issue_type: str,
    state_code: str,
    product_type: str | None,
) -> dict[str, Any]:
    """Fetch online sources and synthesize SLA-shaped fields from closest matches."""
    if not api_keys_configured():
        raise ValueError(
            'No compliance API keys configured. Set GOVINFO_API_KEY or DATA_GOV_API_KEY '
            '(GovInfo / api.data.gov) and/or OPEN_STATES_API_KEY. '
            'For offline unit tests only, set LEGAL_MCP_USE_MOCK_FALLBACK=1.'
        )

    issue_key = normalize_issue(issue_type)
    state = state_code.strip().upper()
    prod = _normalize_product_token(product_type)

    q_gov = govinfo_query(state_code=state, product_token=prod, issue_type=issue_type)
    q_state = open_states_query(product_token=prod, issue_type=issue_type)

    federal = fetch_govinfo_citations(query=q_gov)
    state_bills = fetch_open_states_bills(state_code=state, query=q_state)

    combined = [*federal, *state_bills]
    if not combined:
        raise ValueError(
            'no_online_results: GovInfo and Open States returned no documents. '
            'Verify API keys, rate limits, and try a broader issue description.'
        )

    ranked = rank_citations(
        combined,
        issue_type=issue_type,
        product_token=prod,
        state_code=state,
    )
    top = ranked[0]

    texts: list[str] = []
    for c in ranked[:8]:
        texts.append(c.get('excerpt', ''))
        texts.append(c.get('title', ''))
    sla = extract_timeframe_hint(*texts)
    if not sla:
        sla = (
            'No explicit day-count deadline found in retrieved excerpts; '
            'confirm timelines in the cited official sources.'
        )

    regulatory_basis = (
        f"Closest retrieved authority (ranked by keyword relevance, not legal advice): "
        f"{top.get('title', '')[:400]} — {top.get('url', '')}"
    )

    actions = _build_actions(federal, state_bills, ranked)

    return {
        'issue_type': issue_key,
        'state_code': state,
        'sla_window': sla,
        'required_actions': actions,
        'regulatory_basis': regulatory_basis[:4000],
        'product_type': prod,
        'legal_citations': ranked[:25],
        'source': 'live_apis',
        'search_queries': {'govinfo': q_gov, 'open_states': q_state},
    }


def _normalize_product_token(product_type: str | None) -> str | None:
    if not product_type:
        return None
    token = product_type.strip().upper().replace('-', '_').replace(' ', '_')
    token = ''.join(c for c in token if c.isalnum() or c == '_')
    return token or None


def _build_actions(
    federal: list[dict[str, str]],
    state_bills: list[dict[str, str]],
    ranked: list[dict[str, str]],
) -> list[str]:
    actions: list[str] = []
    if federal:
        t = federal[0].get('title', 'Federal result')[:200]
        actions.append(f'Open and review the top GovInfo match: {t}')
    if state_bills:
        t = state_bills[0].get('title', 'State bill')[:200]
        actions.append(f'Review the top Open States bill match: {t}')
    if not actions and ranked:
        t = ranked[0].get('title', '')[:200]
        actions.append(f'Review the top retrieved source: {t}')
    actions.append('Confirm effective dates, preemption, and exceptions using the linked official texts.')
    actions.append('Escalate to compliance/legal review if obligations remain ambiguous.')
    return actions[:12]
