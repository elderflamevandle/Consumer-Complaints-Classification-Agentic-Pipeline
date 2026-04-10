"""Minimal JSON HTTP helpers (stdlib only)."""

from __future__ import annotations

import json
from typing import Any
from urllib.request import Request, urlopen


def post_json(
    url: str,
    *,
    body: dict[str, Any],
    headers: dict[str, str] | None = None,
    timeout_seconds: float = 25.0,
) -> dict[str, Any]:
    merged = {'Content-Type': 'application/json', 'Accept': 'application/json'}
    if headers:
        merged.update(headers)
    request = Request(
        url,
        method='POST',
        headers=merged,
        data=json.dumps(body).encode('utf-8'),
    )
    with urlopen(request, timeout=timeout_seconds) as response:
        raw = response.read().decode('utf-8')
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError('Expected JSON object response')
    return payload


def get_json(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout_seconds: float = 25.0,
) -> dict[str, Any]:
    request = Request(url, method='GET', headers=headers or {})
    with urlopen(request, timeout=timeout_seconds) as response:
        raw = response.read().decode('utf-8')
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError('Expected JSON object response')
    return payload
