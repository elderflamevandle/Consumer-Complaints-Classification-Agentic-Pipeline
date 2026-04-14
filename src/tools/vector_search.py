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

import yaml
import requests
from pydantic import BaseModel, ConfigDict, Field

_CONFIG_PATH = Path(__file__).parents[2] / 'config.yaml'


def _vs_cfg() -> dict:
    with open(_CONFIG_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f).get('vector_search', {})


def _paths_cfg() -> dict:
    with open(_CONFIG_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f).get('paths', {})


_cfg = _vs_cfg()
DEFAULT_INDEX_DIR = Path(_paths_cfg().get('chroma_dir', 'chroma_db'))

# Number of candidates to fetch from ChromaDB before reranking.
_CANDIDATE_POOL: int = _cfg.get('candidate_pool', 10)

# HuggingFace cross-encoder model used for reranking.
_RERANK_MODEL: str = _cfg.get('rerank_model', 'BAAI/bge-reranker-v2-m3')
_HF_API_BASE: str = _cfg.get('hf_api_base', 'https://router.huggingface.co/hf-inference/models')
_RERANK_TIMEOUT: int = _cfg.get('rerank_timeout_s', 30)

_SEP = '  ' + '-' * 66


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
) -> tuple[list[RetrievedCase], list[float]]:
    """Rerank candidates using a HuggingFace cross-encoder.

    Returns (reranked_candidates, rerank_scores).
    On any failure returns (original_candidates, []) so the caller can detect fallback.
    """
    if not candidates:
        return [], []

    pairs = [{'text': query_text, 'text_pair': c.narrative} for c in candidates]
    url = f'{_HF_API_BASE}/{model}'
    headers = {'Authorization': f'Bearer {hf_token}'}

    try:
        response = requests.post(
            url,
            headers=headers,
            json={'inputs': pairs},
            timeout=_RERANK_TIMEOUT,
        )
        response.raise_for_status()
        raw = response.json()
    except Exception as exc:
        # Network error, timeout, or non-2xx — preserve original order.
        print(f'  [RERANKER] WARNING: API call failed ({exc.__class__.__name__}: {exc})')
        print('  [RERANKER] Falling back to cosine-similarity order.')
        return candidates, []

    # HF router returns scores wrapped in one outer list:
    #   [[{"label":"LABEL_0","score":0.9}, {"label":"LABEL_0","score":0.2}, ...]]
    # Unwrap the outer batch dimension if present.
    if (
        isinstance(raw, list)
        and len(raw) == 1
        and isinstance(raw[0], list)
        and len(raw[0]) == len(candidates)
    ):
        raw = raw[0]

    # Each element is now one of:
    #   • dict:  {"label": "LABEL_0", "score": 0.9}
    #   • float: 0.9
    scores: list[float] = []
    for item in raw:
        if isinstance(item, dict):
            scores.append(float(item.get('score', 0.0)))
        elif isinstance(item, list):
            best = max(item, key=lambda x: x.get('score', 0.0))
            scores.append(float(best.get('score', 0.0)))
        elif isinstance(item, (int, float)):
            scores.append(float(item))
        else:
            scores.append(0.0)

    if len(scores) != len(candidates):
        print(f'  [RERANKER] WARNING: received {len(scores)} scores for {len(candidates)} candidates.')
        print('  [RERANKER] Falling back to cosine-similarity order.')
        return candidates, []

    ranked_pairs = sorted(
        zip(scores, candidates),
        key=lambda pair: pair[0],
        reverse=True,
    )
    reranked = [case for _, case in ranked_pairs]
    final_scores = [s for s, _ in ranked_pairs]
    return reranked, final_scores


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

    # ------------------------------------------------------------------
    # Print: ChromaDB candidate pool
    # ------------------------------------------------------------------
    print(f'\n  [RERANKER] ChromaDB fetched {len(candidates)} candidates (cosine similarity)')
    print(_SEP)
    for rank, c in enumerate(candidates, start=1):
        snippet = c.narrative[:60].replace('\n', ' ')
        print(
            f'  #{rank:02d}  cosine={c.score:.4f}  id={c.id:<10}'
            f'  {c.issue[:35]:<35}  "{snippet}..."'
        )
    print(_SEP)

    # ------------------------------------------------------------------
    # Rerank with HuggingFace cross-encoder when a token is available.
    # ------------------------------------------------------------------
    hf_token = os.environ.get('HF_TOKEN', '')
    if not hf_token:
        print('  [RERANKER] HF_TOKEN not set — skipping rerank, using cosine order.')
        return candidates[:max(limit, 0)]

    # Build a map of cosine rank for the "promoted/dropped" annotation
    cosine_rank_of: dict[str, int] = {c.id: i + 1 for i, c in enumerate(candidates)}

    print(f'\n  [RERANKER] Calling HF cross-encoder: {_RERANK_MODEL}')
    reranked, rerank_scores = _rerank_with_hf(query_text, candidates, hf_token)

    if not rerank_scores:
        # Fallback already printed inside _rerank_with_hf
        return candidates[:max(limit, 0)]

    # ------------------------------------------------------------------
    # Print: reranked order with movement annotations
    # ------------------------------------------------------------------
    print(f'  [RERANKER] Reranked — selecting top {limit} of {len(reranked)}:')
    print(_SEP)
    for new_rank, (c, rs) in enumerate(zip(reranked[:limit], rerank_scores[:limit]), start=1):
        old_rank = cosine_rank_of[c.id]
        if old_rank < new_rank:
            movement = f'v dropped  (was #{old_rank:02d})'
        elif old_rank > new_rank:
            movement = f'^ promoted (was #{old_rank:02d})'
        else:
            movement = f'= no change'
        snippet = c.narrative[:55].replace('\n', ' ')
        print(
            f'  #{new_rank:02d}  rerank={rs:.4f}  cosine={c.score:.4f}  id={c.id:<10}'
            f'  {movement}   "{snippet}..."'
        )
    print(_SEP)

    return reranked[:max(limit, 0)]
