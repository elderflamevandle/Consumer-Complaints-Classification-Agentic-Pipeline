from __future__ import annotations

from pathlib import Path

import pytest

from scripts.seed_vectordb import seed_storage, verify_chroma_collection
from src.tools.vector_index import CHROMA_COLLECTION_NAME


@pytest.fixture
def tiny_embeddings() -> list[list[float]]:
    dim = 384
    return [[float(i) / dim for i in range(dim)], [float(-i) / dim for i in range(dim)]]


def test_seed_storage_writes_chroma_and_count_matches(tmp_path: Path, tiny_embeddings: list[list[float]]) -> None:
    index_dir = tmp_path / 'chroma_db'
    ids = ['c1', 'c2']
    texts = ['narrative one about billing', 'narrative two about fraud']
    metadatas = [
        {'id': 'c1', 'product': 'Credit card', 'issue': 'Billing', 'state': 'CA', 'date': '2025-01-01'},
        {'id': 'c2', 'product': 'Mortgage', 'issue': 'Payment', 'state': 'NY', 'date': '2025-01-02'},
    ]

    seed_storage(
        index_dir=index_dir,
        ids=ids,
        texts=texts,
        metadatas=metadatas,
        embeddings=tiny_embeddings,
    )

    assert (index_dir / 'chroma.sqlite3').exists()

    import chromadb

    client = chromadb.PersistentClient(path=str(index_dir))
    collection = client.get_collection(CHROMA_COLLECTION_NAME)
    assert collection.count() == 2
    verification = verify_chroma_collection(index_dir=index_dir)
    assert verification['count'] == 2
    assert verification['sample_ids']
    got = collection.get(ids=['c1'], include=['documents', 'embeddings'])
    assert got['documents'] and 'billing' in (got['documents'][0] or '')
