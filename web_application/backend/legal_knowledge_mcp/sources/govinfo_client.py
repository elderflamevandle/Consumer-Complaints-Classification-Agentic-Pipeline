"""GovInfo Search API (federal) — requires api.data.gov / GovInfo API key."""

from __future__ import annotations

import os
from typing import Any

from urllib.parse import urlencode

from legal_knowledge_mcp.http_util import get_json, post_json


def fetch_govinfo_citations(
    *,
    query: str,
    timeout_seconds: float = 25.0,
    max_items: int = 8,
) -> list[dict[str, str]]:
    """Return citation dicts from GovInfo search (POST /search)."""
    api_key = (os.environ.get('GOVINFO_API_KEY') or os.environ.get('DATA_GOV_API_KEY') or '').strip()
    if not api_key:
        return []

    url = 'https://api.govinfo.gov/search'
    body: dict[str, Any] = {
        'query': query,
        'pageSize': max(1, min(max_items, 20)),
        'offsetMark': '*',
        'sorts': [{'field': 'score', 'sortOrder': 'DESC'}],
    }
    headers = {'X-Api-Key': api_key}

    try:
        payload = post_json(url, body=body, headers=headers, timeout_seconds=timeout_seconds)
    except Exception:
        payload = {}

    citations = _records_to_citations(payload, max_items=max_items)
    if citations:
        return citations

    # Some deployments accept GET search; try as secondary path.
    try:
        get_url = f'{url}?{urlencode({"q": query, "pageSize": max(1, min(max_items, 20))})}'
        payload_get = get_json(get_url, headers=headers, timeout_seconds=timeout_seconds)
    except Exception:
        return []

    return _records_to_citations(payload_get, max_items=max_items)


def _records_to_citations(payload: dict[str, Any], *, max_items: int) -> list[dict[str, str]]:
    items: list[dict[str, Any]] = []

    data = payload.get('data')
    if isinstance(data, list):
        items = [x for x in data if isinstance(x, dict)]
    elif isinstance(data, dict):
        inner = data.get('items') or data.get('results')
        if isinstance(inner, list):
            items = [x for x in inner if isinstance(x, dict)]

    if not items:
        for key in ('results', 'items'):
            block = payload.get(key)
            if isinstance(block, list):
                items = [x for x in block if isinstance(x, dict)]
                break

    if not items:
        nested = payload.get('results')
        if isinstance(nested, dict):
            inner = nested.get('items') or nested.get('results')
            if isinstance(inner, list):
                items = [x for x in inner if isinstance(x, dict)]

    out: list[dict[str, str]] = []
    for item in items[:max_items]:
        title = str(
            item.get('title')
            or item.get('name')
            or item.get('description')
            or 'GovInfo document'
        )
        link = str(
            item.get('link')
            or item.get('url')
            or item.get('pdfLink')
            or item.get('packageLink')
            or 'https://www.govinfo.gov/'
        )
        excerpt = str(
            item.get('snippet')
            or item.get('summary')
            or item.get('teaser')
            or item.get('description')
            or ''
        )
        pkg = item.get('packageId')
        if pkg and link == 'https://www.govinfo.gov/':
            link = f'https://www.govinfo.gov/app/details/{pkg}'

        out.append(
            {
                'title': title[:500],
                'url': link[:2000],
                'publisher': 'GovInfo (U.S. GPO)',
                'excerpt': excerpt[:2000],
                'layer': 'federal',
            }
        )
    return out
