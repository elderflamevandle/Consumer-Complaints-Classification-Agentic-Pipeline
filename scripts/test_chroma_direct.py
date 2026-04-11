"""Simple smoke checks for a seeded Chroma collection."""

from pathlib import Path

import chromadb

from scripts.seed_vectordb import verify_chroma_collection
from src.tools.hf_embedding_api import embed_texts
from src.tools.vector_index import CHROMA_COLLECTION_NAME, read_manifest


def test_chroma():
    index_dir = Path('chroma_db')
    if not index_dir.exists():
        print(f'Error: Directory {index_dir} does not exist.')
        return

    print(f'Initializing ChromaDB persistent client at {index_dir}...')
    client = chromadb.PersistentClient(path=str(index_dir))

    collections = client.list_collections()
    collection_names = [col.name for col in collections]
    print(f'Available collections: {collection_names}')

    if CHROMA_COLLECTION_NAME not in collection_names:
        print(
            f"Required collection {CHROMA_COLLECTION_NAME!r} not found. "
            'Ensure seeding succeeded with ChromaDB.'
        )
        return

    verification = verify_chroma_collection(index_dir=index_dir)
    print(
        f"Collection {CHROMA_COLLECTION_NAME!r} has {verification['count']} documents. "
        f"Sample IDs: {verification['sample_ids']}"
    )

    collection = client.get_collection(name=CHROMA_COLLECTION_NAME)
    count = collection.count()
    if count == 0:
        print('Collection is empty.')
        return

    peek = collection.peek(limit=min(2, count))
    print(f"Peek IDs: {peek.get('ids') or []}")

    query_text = "My bank account was closed without notice and my funds are frozen."
    print(f"\nQuerying database for: '{query_text}'")

    try:
        manifest = read_manifest(index_dir)
        embedding_model = manifest.embedding_model if manifest else None
        query_embeddings = embed_texts(
            [query_text],
            embedding_model=embedding_model or 'sentence-transformers/all-MiniLM-L6-v2',
        )
        results = collection.query(
            query_embeddings=query_embeddings,
            n_results=3,
            include=['documents', 'metadatas', 'distances'],
        )

        print('\nResults:')
        for i in range(len(results["ids"][0])):
            doc_id = results["ids"][0][i]
            distance = results["distances"][0][i] if results["distances"] else 'N/A'
            metadata = results["metadatas"][0][i]
            doc = results["documents"][0][i]
            
            print(f"[{i+1}] ID: {doc_id} | Distance: {distance} | Issue: {metadata.get('issue')}")
            print(f"    Product: {metadata.get('product')}")
            print(f"    Snippet: {doc[:150]}...")
            print('-' * 60)

    except Exception as e:
        print(f'\nError querying ChromaDB: {e}')
        print('Smoke checks passed up to collection inspection, but remote embedding query failed.')

if __name__ == "__main__":
    test_chroma()
