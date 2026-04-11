"""Deterministic retrieval helpers for top-k similar complaint context using ChromaDB."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

DEFAULT_INDEX_DIR = Path('chroma_db')


class RetrievedCase(BaseModel):
    model_config = ConfigDict(extra='forbid')

    id: str
    product: str
    issue: str
    date: str
    state: str | None = None
    narrative: str
    score: float = Field(ge=0.0)


def retrieve_similar_cases(
    *,
    query_text: str,
    limit: int = 5,
    index_dir: Path = DEFAULT_INDEX_DIR,
) -> list[RetrievedCase]:
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

    results = collection.query(
        query_texts=[query_text],
        n_results=max(limit, 1),
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

    return sorted(candidates, key=lambda item: (-item.score, item.id))[:max(limit, 0)]
