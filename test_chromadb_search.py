"""
Standalone ChromaDB vector search test.

Run: python test_chromadb_search.py
Requires: chroma_db/ directory already seeded (run scripts/seed_vectordb.py first).
"""

from __future__ import annotations

from pathlib import Path

CHROMA_DIR = Path("chroma_db")
COLLECTION_NAME = "cfpb_complaints"


def test_collection_exists() -> None:
    import chromadb

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    names = [c.name for c in client.list_collections()]
    print(f"[collection_exists] Collections found: {names}")
    assert COLLECTION_NAME in names, f"Expected '{COLLECTION_NAME}' in {names}"
    print("[collection_exists] PASS\n")


def test_collection_count() -> None:
    import chromadb

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    col = client.get_collection(COLLECTION_NAME)
    count = col.count()
    print(f"[collection_count] Records in collection: {count}")
    assert count > 0, "Collection is empty — re-run seed_vectordb.py"
    print("[collection_count] PASS\n")


def test_basic_query() -> None:
    import chromadb

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    col = client.get_collection(COLLECTION_NAME)

    query = "I was charged twice on my credit card and the bank refused to refund me"
    print(f"[basic_query] Query: '{query[:60]}...'")

    results = col.query(query_texts=[query], n_results=5)

    ids = results["ids"][0]
    distances = results["distances"][0]
    metadatas = results["metadatas"][0]
    documents = results["documents"][0]

    print(f"[basic_query] Got {len(ids)} results")
    for i, (rid, dist, meta, doc) in enumerate(zip(ids, distances, metadatas, documents)):
        score_wrong = max(0.0, 1.0 - dist)   # current buggy formula
        score_fixed = 1.0 / (1.0 + dist)     # better formula for L2
        print(
            f"  #{i+1}  id={rid}  dist={dist:.4f}  "
            f"score_current={score_wrong:.4f}  score_fixed={score_fixed:.4f}"
        )
        print(f"       product={meta.get('product')}  issue={meta.get('issue')}  state={meta.get('state')}")
        print(f"       narrative_preview: {doc[:80]}...")
    print("[basic_query] PASS\n")


def test_distance_metric() -> None:
    """
    Verify what distance metric ChromaDB is using.
    Useful to confirm the score formula needs fixing.
    """
    import chromadb

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    col = client.get_collection(COLLECTION_NAME)
    metadata = col.metadata
    print(f"[distance_metric] Collection metadata: {metadata}")
    metric = metadata.get("hnsw:space", "l2") if metadata else "l2"
    print(f"[distance_metric] Distance metric in use: {metric}")
    if metric == "l2":
        print("  WARNING: L2 distances are unbounded. '1.0 - distance' score formula is WRONG.")
        print("  Fix: use collection with hnsw:space=cosine, or use 1/(1+distance) formula.")  # noqa: E501
    elif metric == "cosine":
        print("  OK: cosine distance in [0, 2]. Score formula '1 - distance' gives [-1, 1], capped to [0, 1].")
    print("[distance_metric] PASS\n")


def test_empty_query_fallback() -> None:
    """Verify retrieve_similar_cases returns [] when collection missing."""
    from src.tools.vector_search import retrieve_similar_cases

    results = retrieve_similar_cases(
        query_text="test complaint",
        limit=3,
        index_dir=Path("nonexistent_chroma_dir_xyz"),
    )
    assert results == [], f"Expected [], got {results}"
    print("[empty_query_fallback] PASS — returns [] for missing index\n")


def test_retrieve_similar_cases_wrapper() -> None:
    """Test the actual retrieve_similar_cases() wrapper used by the pipeline."""
    from src.tools.vector_search import retrieve_similar_cases

    query = "fraudulent charges on my bank account the bank ignored my dispute"
    results = retrieve_similar_cases(query_text=query, limit=3, index_dir=CHROMA_DIR)

    print(f"[wrapper] Got {len(results)} RetrievedCase objects")
    for case in results:
        print(f"  id={case.id}  score={case.score}  product={case.product}  issue={case.issue}")
        print(f"  narrative_preview: {case.narrative[:80]}...")

    # score bug check: if all scores are 0.0, the formula is wrong
    if results:
        max_score = max(c.score for c in results)
        if max_score == 0.0:
            print("  BUG CONFIRMED: all scores are 0.0 — L2 distances > 1.0, formula '1-dist' broken.")
        else:
            print(f"  Scores look OK (max={max_score})")
    print("[wrapper] PASS\n")


def test_manifest() -> None:
    """Check manifest correctness."""
    import json

    manifest_path = CHROMA_DIR / "manifest.json"
    assert manifest_path.exists(), "manifest.json missing"
    manifest = json.loads(manifest_path.read_text())
    print(f"[manifest] embedding_model recorded: {manifest.get('embedding_model')}")
    print(f"[manifest] record_count: {manifest.get('record_count')}")
    print(f"[manifest] created_at: {manifest.get('created_at')}")
    if manifest.get("embedding_model") == "bge-large-en-v1.5":
        print("  WARNING: Manifest says 'bge-large-en-v1.5' but ChromaDB used its built-in MiniLM.")
        print("  The manifest.embedding_model field is misleading.")
    print("[manifest] PASS\n")


def main() -> None:
    print("=" * 60)
    print("ChromaDB Vector Search Test Suite")
    print("=" * 60, "\n")

    tests = [
        test_collection_exists,
        test_collection_count,
        test_distance_metric,
        test_manifest,
        test_basic_query,
        test_empty_query_fallback,
        test_retrieve_similar_cases_wrapper,
    ]

    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as exc:
            print(f"FAIL [{t.__name__}]: {exc}\n")
            failed += 1

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)


if __name__ == "__main__":
    main()
