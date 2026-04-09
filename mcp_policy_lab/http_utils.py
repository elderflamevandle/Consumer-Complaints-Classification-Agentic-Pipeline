from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def get_json(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    query: dict[str, str] | None = None,
    timeout_seconds: float = 20.0,
) -> dict[str, Any]:
    full_url = url
    if query:
        full_url = f"{url}?{urlencode(query)}"

    request = Request(full_url, method="GET", headers=headers or {})
    with urlopen(request, timeout=timeout_seconds) as response:
        body = response.read().decode("utf-8")
    payload = json.loads(body)
    if not isinstance(payload, dict):
        raise ValueError("Expected JSON object response")
    return payload


def post_json(
    url: str,
    *,
    body: dict[str, Any],
    headers: dict[str, str] | None = None,
    timeout_seconds: float = 20.0,
) -> dict[str, Any]:
    merged_headers = {"Content-Type": "application/json"}
    if headers:
        merged_headers.update(headers)

    request = Request(
        url,
        method="POST",
        headers=merged_headers,
        data=json.dumps(body).encode("utf-8"),
    )
    with urlopen(request, timeout=timeout_seconds) as response:
        raw = response.read().decode("utf-8")
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("Expected JSON object response")
    return payload

