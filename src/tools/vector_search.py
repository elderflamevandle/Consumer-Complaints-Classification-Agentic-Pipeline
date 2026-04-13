"""Deterministic retrieval helpers for top-k similar complaint context using ChromaDB.

Retrieval pipeline:
  1. Fetch up to CANDIDATE_POOL (10) records from ChromaDB via cosine similarity.
  2. Rerank those candidates using a HuggingFace cross-encoder (BAAI/bge-reranker-v2-m3).
  3. Return the top `limit` results (default 5) after reranking.

If HF_TOKEN is absent or the rerank API call fails, the function falls back to the
original cosine-similarity ranking so the rest of the pipeline is never blocked.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import requests
from pydantic import BaseModel, ConfigDict, Field

DEFAULT_INDEX_DIR = Path('chroma_db')

# Number of candidates to fetch from ChromaDB before reranking.
_CANDIDATE_POOL = 10

# HuggingFace cross-encoder model used for reranking.
_RERANK_MODEL = 'BAAI/bge-reranker-v2-m3'
_HF_API_BASE = 'https://api-inference.huggingface.co/models'


class RetrievedCase(BaseModel):
    model_config = ConfigDict(extra='forbid')

    id: str
    product: str
    issue: str
    date: str
    state: str | None = None
    narrative: str
    score: float = Field(ge=0.0)


def _rerank_with_hf(
    query_text: str,
    candidates: list[RetrievedCase],
    hf_token: str,
    model: str = _RERANK_MODEL,
) -> list[RetrievedCase]:
    """Rerank candidates using a HuggingFace cross-encoder.

    Sends (query, narrative) pairs to the HF Inference API and returns
    candidates sorted by descending relevance score.  Falls back to the
    original order if the API call fails or returns a malformed response.
    """
    if not candidates:
        return []

    pairs = [[query_text, c.narrative] for c in candidates]
    url = f'{_HF_API_BASE}/{model}'
    headers = {'Authorization': f'Bearer {hf_token}'}

    try:
        response = requests.post(
            url,
            headers=headers,
            json={'inputs': pairs},
            timeout=30,
        )
        response.raise_for_status()
        raw = response.json()
    except Exception:
        # Network error, timeout, or non-2xx — preserve original order.
        return candidates

    # HF cross-encoders return one of two shapes per pair:
    #   • list of dicts: [{"label": "1", "score": 0.9}, ...]
    #   • bare float: 0.9
    scores: list[float] = []
    for item in raw:
        if isinstance(item, list):
            # Pick the entry with the highest score (the "relevant" class).
            best = max(item, key=lambda x: x.get('score', 0.0))
            scores.append(float(best.get('score', 0.0)))
        elif isinstance(item, (int, float)):
            scores.append(float(item))
        else:
            scores.append(0.0)

    if len(scores) != len(candidates):
        # Malformed response — keep original cosine-similarity order.
        return candidates

    ranked = sorted(
        zip(scores, candidates),
        key=lambda pair: pair[0],
        reverse=True,
    )
    return [case for _, case in ranked]


def retrieve_similar_cases(
    *,
    query_text: str,
    limit: int = 5,
    index_dir: Path = DEFAULT_INDEX_DIR,
) -> list[RetrievedCase]:
    """Retrieve the top `limit` similar complaints for *query_text*.

    Fetches _CANDIDATE_POOL (10) candidates from ChromaDB, reranks them via
    a HuggingFace cross-encoder, and returns the top `limit` results.
    """
    try:
        import chromadb
    except ImportError:
        raise RuntimeError('chromadb is required for vector search.')

    client = chromadb.PersistentClient(path=str(index_dir))
    collection_name = 'cfpb_complaints'

    try:
        collection = client.get_collection(name=collection_name)
    except Exception:
        return []

    # Always fetch at least _CANDIDATE_POOL records for reranking.
    fetch_n = max(_CANDIDATE_POOL, limit)

    results = collection.query(
        query_texts=[query_text],
        n_results=max(fetch_n, 1),
    )

    if not results or not results['ids'] or not results['ids'][0]:
        return []

    ids = results['ids'][0]
    documents = results['documents'][0] if results['documents'] else []
    metadatas = results['metadatas'][0] if results['metadatas'] else []
    distances = results['distances'][0] if results['distances'] else []

    candidates: list[RetrievedCase] = []

    for i in range(len(ids)):
        meta: dict[str, Any] = (
            metadatas[i] if i < len(metadatas) and metadatas[i] is not None else {}
        )
        narrative = documents[i] if i < len(documents) and documents[i] is not None else ''
        distance = distances[i] if i < len(distances) else 1.0

        # Collection uses cosine distance (range [0, 2]).
        # score = 1 - distance maps identical→1.0, orthogonal→0.0.
        score = max(0.0, 1.0 - float(distance))

        candidates.append(
            RetrievedCase(
                id=ids[i],
                product=meta.get('product', 'Unknown'),
                issue=meta.get('issue', 'Unknown'),
                date=meta.get('date', 'Unknown'),
                state=meta.get('state'),
                narrative=narrative,
                score=round(score, 6),
            )
        )

    # Sort by cosine similarity so the fallback order is already sensible.
    candidates = sorted(candidates, key=lambda item: (-item.score, item.id))

    # Rerank with HuggingFace cross-encoder when a token is available.
    hf_token = os.environ.get('HF_TOKEN', '')
    if hf_token:
        candidates = _rerank_with_hf(query_text, candidates, hf_token)

    return candidates[:max(limit, 0)]
