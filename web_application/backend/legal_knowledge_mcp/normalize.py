"""Issue-type normalisation (shared with tests and policy lookup)."""

from __future__ import annotations

import re


def normalize_issue(issue_type: str) -> str:
    """Normalise a raw issue-type string to an uppercase underscore-delimited key.

    Whitespace and hyphens are collapsed to single underscores.
    All characters that are not A-Z, 0-9, or underscore are removed.
    Non-ASCII letters (e.g. accented characters) are dropped entirely.
    """
    normalized = issue_type.strip().upper()
    normalized = re.sub(r'[\s-]+', '_', normalized)
    normalized = re.sub(r'[^A-Z0-9_]', '', normalized)
    return normalized
