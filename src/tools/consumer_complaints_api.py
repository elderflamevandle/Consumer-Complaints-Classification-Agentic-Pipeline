"""Consumer complaint ingestion helpers for the CFPB complaints search API."""

from __future__ import annotations

from typing import Any

DEFAULT_CFPB_COMPLAINTS_API = (
    'https://www.consumerfinance.gov/data-research/consumer-complaints/search/api/v1/'
)


def _extract_records(response_json: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ('results', 'data', 'items', 'hits'):
        value = response_json.get(key)
        if isinstance(value, list):
            return value

    payload = response_json.get('payload')
    if isinstance(payload, dict):
        for key in ('results', 'data', 'items', 'hits'):
            value = payload.get(key)
            if isinstance(value, list):
                return value

    return []


def fetch_complaint_records(
    api_url: str = DEFAULT_CFPB_COMPLAINTS_API,
    *,
    page_param: str = 'page',
    size_param: str = 'size',
    page_size: int = 100,
    max_pages: int = 5,
    query_params: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    try:
        import requests
    except Exception as error:
        raise RuntimeError(
            'requests is required to fetch data from the complaints API. '
            'Install it with `pip install requests` or `uv add requests`.'
        ) from error

    params: dict[str, str] = dict(query_params or {})
    records: list[dict[str, Any]] = []

    for page in range(1, max_pages + 1):
        params[page_param] = str(page)
        params[size_param] = str(page_size)

        response = requests.get(api_url, params=params, timeout=30)
        response.raise_for_status()
        page_data = response.json()
        page_records = _extract_records(page_data)

        if not page_records:
            break

        records.extend(page_records)
        if len(page_records) < page_size:
            break

    return records
