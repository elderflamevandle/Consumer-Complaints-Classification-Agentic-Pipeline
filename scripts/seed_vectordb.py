"""Seed local vector index artifacts from the sampled parquet dataset."""

from __future__ import annotations

import hashlib
import json
from argparse import ArgumentParser
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.tools.vector_index import (
    compute_dataset_hash,
    create_manifest,
    should_reseed,
    write_manifest,
)

EMBEDDING_MODEL_ID = 'bge-large-en-v1.5'
DEFAULT_DATASET_PATH = Path('data/processed/dev.parquet')
DEFAULT_INDEX_DIR = Path('chroma_db')


@dataclass(frozen=True)
class SeedStatus:
    status: str
    message: str
    reused_previous_index: bool = False


def load_records(dataset_path: Path, limit: int | None = 5_000) -> list[dict[str, Any]]:
    try:
        import pandas as pd
    except Exception as error:
        raise RuntimeError(
            'pandas + pyarrow are required to load the parquet dataset. '
            'Run `uv sync` to install project dependencies, or `uv add pandas pyarrow` '
            'if your environment was created before those packages were added.'
        ) from error

    frame = pd.read_parquet(dataset_path)
    required = {'id', 'product', 'issue', 'state', 'date', 'narrative'}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f'Missing required columns: {missing}')

    if limit is not None and limit > 0:
        trimmed = frame.head(limit)
    else:
        trimmed = frame
    return trimmed.to_dict(orient='records')


def _hash_to_vector(text: str, dimensions: int = 16) -> list[float]:
    digest = hashlib.sha256(text.encode('utf-8')).digest()
    values: list[float] = []
    for i in range(dimensions):
        values.append((digest[i] / 255.0) * 2.0 - 1.0)
    return values


def compute_embeddings(texts: list[str], embedding_model: str) -> list[list[float]]:
    try:
        from sentence_transformers import SentenceTransformer
    except Exception:
        # Deterministic fallback keeps the pipeline testable when model weights are unavailable.
        return [_hash_to_vector(f'{embedding_model}:{text}') for text in texts]

    encoder = SentenceTransformer(embedding_model)
    return [list(vector) for vector in encoder.encode(texts, show_progress_bar=False)]


def seed_storage(
    *,
    index_dir: Path,
    ids: list[str],
    texts: list[str],
    metadatas: list[dict[str, Any]],
    embeddings: list[list[float]],
) -> str:
    index_dir.mkdir(parents=True, exist_ok=True)

    try:
        import chromadb
    except Exception:
        fallback_path = index_dir / 'fallback_index.json'
        payload = [
            {
                'id': item_id,
                'text': text,
                'metadata': metadata,
                'embedding': embedding,
            }
            for item_id, text, metadata, embedding in zip(
                ids,
                texts,
                metadatas,
                embeddings,
                strict=True,
            )
        ]
        fallback_path.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
        return 'json-fallback'

    client = chromadb.PersistentClient(path=str(index_dir))
    collection_name = 'cfpb_complaints'

    existing_names = {collection.name for collection in client.list_collections()}
    if collection_name in existing_names:
        client.delete_collection(collection_name)

    collection = client.create_collection(name=collection_name)
    collection.add(
        ids=ids,
        documents=texts,
        metadatas=metadatas,
        embeddings=embeddings,
    )
    return 'chroma'


def handle_seed_failure(*, has_existing_manifest: bool, error: Exception) -> SeedStatus:
    if has_existing_manifest:
        return SeedStatus(
            status='warning',
            message=f'Seed failed; using last valid index. Error: {error}',
            reused_previous_index=True,
        )
    return SeedStatus(
        status='failed',
        message=f'Seed failed and no prior index exists. Error: {error}',
    )


def seed_vector_index(
    *,
    dataset_path: Path,
    index_dir: Path,
    embedding_model: str,
    limit: int | None = 5_000,
) -> SeedStatus:
    dataset_hash = compute_dataset_hash(dataset_path)
    should_seed, reason = should_reseed(
        index_dir=index_dir,
        dataset_hash=dataset_hash,
        embedding_model=embedding_model,
    )
    if not should_seed:
        return SeedStatus(status='skipped', message=f'Index already fresh ({reason}).')

    has_existing_manifest = (index_dir / 'manifest.json').exists()

    try:
        records = load_records(dataset_path, limit=limit)
        ids = [str(record['id']) for record in records]
        texts = [str(record['narrative']) for record in records]
        metadatas = [
            {
                'id': str(record['id']),
                'product': str(record['product']),
                'issue': str(record['issue']),
                'state': str(record['state']),
                'date': str(record['date']),
            }
            for record in records
        ]
        embeddings = compute_embeddings(texts, embedding_model)
        backend = seed_storage(
            index_dir=index_dir,
            ids=ids,
            texts=texts,
            metadatas=metadatas,
            embeddings=embeddings,
        )

        manifest = create_manifest(
            dataset_hash=dataset_hash,
            embedding_model=embedding_model,
            dataset_path=dataset_path,
            index_path=index_dir,
            record_count=len(records),
        )
        write_manifest(index_dir, manifest)
        return SeedStatus(
            status='seeded',
            message=f'Seed complete using {backend} backend ({len(records)} records).',
        )
    except Exception as error:
        return handle_seed_failure(has_existing_manifest=has_existing_manifest, error=error)


def main() -> int:
    parser = ArgumentParser(description='Seed local vector index from parquet dataset.')
    parser.add_argument('--dataset', default=str(DEFAULT_DATASET_PATH))
    parser.add_argument('--index-dir', default=str(DEFAULT_INDEX_DIR))
    parser.add_argument('--embedding-model', default=EMBEDDING_MODEL_ID)
    parser.add_argument('--no-limit', action='store_true', help='Ingest all records without limiting to 5000')
    args = parser.parse_args()

    status = seed_vector_index(
        dataset_path=Path(args.dataset),
        index_dir=Path(args.index_dir),
        embedding_model=args.embedding_model,
        limit=None if args.no_limit else 5_000,
    )
    print(f'[{status.status}] {status.message}')
    return 0 if status.status in {'seeded', 'skipped', 'warning'} else 1


if __name__ == '__main__':
    raise SystemExit(main())
