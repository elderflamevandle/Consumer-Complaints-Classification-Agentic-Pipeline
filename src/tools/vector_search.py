"""Deterministic retrieval helpers for top-k similar complaint context."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

DEFAULT_INDEX_DIR = Path('chroma_db')
FALLBACK_INDEX_FILE = 'fallback_index.json'


class RetrievedCase(BaseModel):
    model_config = ConfigDict(extra='forbid')

    id: str
    product: str
    issue: str
    date: str
    state: str | None = None
    narrative: str
    score: float = Field(ge=0.0)


def _tokenize(text: str) -> set[str]:
    return {token for token in re.split(r'[^a-zA-Z0-9]+', text.lower()) if token}


def _similarity(query: str, narrative: str) -> float:
    q_tokens = _tokenize(query)
    n_tokens = _tokenize(narrative)
    if not q_tokens or not n_tokens:
        return 0.0
    overlap = len(q_tokens & n_tokens)
    return overlap / float(len(q_tokens | n_tokens))


def _candidate_from_record(record: dict[str, Any], query_text: str) -> RetrievedCase | None:
    metadata = record.get('metadata')
    narrative = record.get('text')
    if not isinstance(metadata, dict) or not isinstance(narrative, str):
        return None

    case_id_raw = metadata.get('id')
    product_raw = metadata.get('product')
    issue_raw = metadata.get('issue')
    date_raw = metadata.get('date')
    state = metadata.get('state')
    if not isinstance(case_id_raw, str):
        return None
    if not isinstance(product_raw, str):
        return None
    if not isinstance(issue_raw, str):
        return None
    if not isinstance(date_raw, str):
        return None

    case_id = case_id_raw
    product = product_raw
    issue = issue_raw
    date = date_raw

    return RetrievedCase(
        id=case_id,
        product=product,
        issue=issue,
        date=date,
        state=state if isinstance(state, str) else None,
        narrative=narrative,
        score=round(_similarity(query_text, narrative), 6),
    )


def load_index_records(index_dir: Path = DEFAULT_INDEX_DIR) -> list[dict[str, Any]]:
    fallback_path = index_dir / FALLBACK_INDEX_FILE
    if not fallback_path.exists():
        return []

    payload = json.loads(fallback_path.read_text(encoding='utf-8'))
    if not isinstance(payload, list):
        return []

    return [item for item in payload if isinstance(item, dict)]


def retrieve_similar_cases(
    *,
    query_text: str,
    limit: int = 5,
    index_dir: Path = DEFAULT_INDEX_DIR,
    records: Iterable[dict[str, Any]] | None = None,
) -> list[RetrievedCase]:
    if records is not None:
        source_records = list(records)
    else:
        source_records = load_index_records(index_dir=index_dir)

    candidates: list[RetrievedCase] = []
    for record in source_records:
        candidate = _candidate_from_record(record, query_text)
        if candidate is not None:
            candidates.append(candidate)

    ranked = sorted(
        candidates,
        key=lambda item: (-item.score, item.id),
    )
    return ranked[: max(limit, 0)]
