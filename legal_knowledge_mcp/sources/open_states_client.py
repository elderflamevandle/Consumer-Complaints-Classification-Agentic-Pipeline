"""Open States API v3 — state bills search (requires OPEN_STATES_API_KEY)."""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlencode

from legal_knowledge_mcp.http_util import get_json
from legal_knowledge_mcp.query_builder import state_jurisdiction_id


def fetch_open_states_bills(
    *,
    state_code: str,
    query: str,
    timeout_seconds: float = 25.0,
    max_items: int = 6,
) -> list[dict[str, str]]:
    api_key = (os.environ.get('OPEN_STATES_API_KEY') or '').strip()
    if not api_key:
        return []

    try:
        jurisdiction = state_jurisdiction_id(state_code)
    except ValueError:
        return []

    params: dict[str, Any] = {
        'jurisdiction': jurisdiction,
        'q': query,
        'page': 1,
        'per_page': max(1, min(max_items, 20)),
        'sort': 'updated_desc',
    }
    url = f'https://v3.openstates.org/bills?{urlencode(params)}'
    headers = {'X-API-KEY': api_key}

    try:
        payload = get_json(url, headers=headers, timeout_seconds=timeout_seconds)
    except Exception:
        return []

    results = payload.get('results')
    if not isinstance(results, list):
        return []

    out: list[dict[str, str]] = []
    for bill in results[:max_items]:
        if not isinstance(bill, dict):
            continue
        title = str(bill.get('title') or 'State bill')
        ident = str(bill.get('identifier') or '')
        link = str(bill.get('openstates_url') or 'https://openstates.org/')
        latest = str(bill.get('latest_action_description') or '')
        excerpt_bits = [ident, latest]
        abstracts = bill.get('abstracts')
        if isinstance(abstracts, list) and abstracts:
            first = abstracts[0]
            if isinstance(first, dict) and first.get('abstract'):
                excerpt_bits.append(str(first.get('abstract')))
        excerpt = ' — '.join(b for b in excerpt_bits if b)

        out.append(
            {
                'title': f'{ident} {title}'.strip()[:500],
                'url': link[:2000],
                'publisher': 'Open States (state legislation)',
                'excerpt': excerpt[:2000],
                'layer': 'state',
            }
        )
    return out
