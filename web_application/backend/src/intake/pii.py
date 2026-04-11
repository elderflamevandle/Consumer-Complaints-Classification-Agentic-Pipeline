"""Typed-token PII scrubbing for intake preprocessing."""

from __future__ import annotations

import re
from typing import Final

from src.schemas.intake import ScrubResult

PatternDef = tuple[str, re.Pattern[str]]

_TYPED_PATTERNS: Final[tuple[PatternDef, ...]] = (
    ('EMAIL', re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b')),
    ('PHONE', re.compile(r'\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b')),
    ('SSN', re.compile(r'\b\d{3}-\d{2}-\d{4}\b')),
    ('CARD', re.compile(r'\b(?:\d[ -]?){13,19}\b')),
)

_NAME_WITH_PREFIX = re.compile(r'\b(?:mr|mrs|ms|dr)\.?\s+[A-Z][a-z]+\b')

_SUSPICIOUS_HINTS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r'\bmy name is\b', re.IGNORECASE),
    re.compile(r'\bcall me\b', re.IGNORECASE),
    re.compile(r'\bcontact me\b', re.IGNORECASE),
    re.compile(r'\breach me\b', re.IGNORECASE),
    re.compile(r'\baccount\b', re.IGNORECASE),
    re.compile(r'\bcard\b', re.IGNORECASE),
    re.compile(r'\bsocial security\b', re.IGNORECASE),
)


def _normalize_text(text: str) -> str:
    return ' '.join(text.strip().split())


def _replace_pattern(text: str, label: str, pattern: re.Pattern[str]) -> tuple[str, int]:
    placeholder = f'[{label}]'
    return pattern.subn(placeholder, text)


def _contains_unresolved_hints(text: str) -> bool:
    return any(pattern.search(text) is not None for pattern in _SUSPICIOUS_HINTS)


def scrub_pii(raw_text: str) -> ScrubResult:
    normalized = _normalize_text(raw_text)
    if not normalized:
        return ScrubResult(
            raw_text=raw_text,
            scrubbed_text='',
            scrub_confidence=0.0,
            redaction_counts={},
            warnings=['empty_input'],
        )

    working = normalized
    redaction_counts: dict[str, int] = {}

    for label, pattern in _TYPED_PATTERNS:
        working, count = _replace_pattern(working, label, pattern)
        if count > 0:
            redaction_counts[label] = redaction_counts.get(label, 0) + count

    working, prefixed_name_count = _replace_pattern(working, 'NAME', _NAME_WITH_PREFIX)
    if prefixed_name_count > 0:
        redaction_counts['NAME'] = redaction_counts.get('NAME', 0) + prefixed_name_count

    total_redactions = sum(redaction_counts.values())
    unresolved_hints = _contains_unresolved_hints(normalized)

    warnings: list[str] = []
    if total_redactions > 0:
        confidence = 0.95
    elif unresolved_hints:
        confidence = 0.45
        warnings.append('possible_pii_unresolved')
    else:
        confidence = 0.85

    return ScrubResult(
        raw_text=raw_text,
        scrubbed_text=working,
        scrub_confidence=confidence,
        redaction_counts=redaction_counts,
        warnings=warnings,
    )