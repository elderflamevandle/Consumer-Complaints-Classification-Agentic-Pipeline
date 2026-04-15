"""Heuristic extraction of timeframe language from regulatory text snippets."""

from __future__ import annotations

import re


def extract_timeframe_hint(*texts: str) -> str | None:
    """Return a short phrase if a day-count pattern appears in combined text."""
    blob = ' '.join(t for t in texts if t).lower()
    if not blob.strip():
        return None

    # N business days / calendar days / days after notice, etc.
    patterns = [
        r'\b(\d{1,3})\s+business\s+days?\b',
        r'\b(\d{1,3})\s+calendar\s+days?\b',
        r'\bwithin\s+(\d{1,3})\s+days?\b',
        r'\b(\d{1,3})\s+days?\s+(?:of|after|from)\b',
        r'\bnot\s+later\s+than\s+(\d{1,3})\s+days?\b',
    ]
    for pat in patterns:
        m = re.search(pat, blob)
        if m:
            n = m.group(1)
            if 'business' in m.group(0):
                return f'{n} business days (extracted from retrieved text; verify at source)'
            if 'calendar' in m.group(0) or 'within' in m.group(0):
                return f'{n} calendar days (extracted from retrieved text; verify at source)'
            return f'{n} days (extracted from retrieved text; verify at source)'
    return None
