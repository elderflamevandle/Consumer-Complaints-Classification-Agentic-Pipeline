"""Seed local vector index artifacts from the sampled parquet dataset."""

from __future__ import annotations

from argparse import ArgumentParser
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import chromadb

from src.tools.hf_embedding_api import DEFAULT_EMBEDDING_MODEL, embed_texts
from src.tools.vector_index import (
    CHROMA_COLLECTION_NAME,
    compute_dataset_hash,
    create_manifest,
    should_reseed,
    write_manifest,
)

EMBEDDING_MODEL_ID = DEFAULT_EMBEDDING_MODEL
DEFAULT_DATASET_PATH = Path('data/processed/dev.parquet')
DEFAULT_INDEX_DIR = Path('chroma_db')
DEFAULT_LIMIT = 20_000
CHROMA_INSERT_BATCH_SIZE = 5_000


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


def seed_storage(
    *,
    index_dir: Path,
    ids: list[str],
    texts: list[str],
    metadatas: list[dict[str, Any]],
    embeddings: list[list[float]],
) -> None:
    """Persist embeddings in Chroma. Raises on failure — no JSON fallback."""
    if len(ids) != len(texts) or len(ids) != len(metadatas) or len(ids) != len(embeddings):
        raise ValueError(
            f'Mismatched lengths: ids={len(ids)} texts={len(texts)} '
            f'metadatas={len(metadatas)} embeddings={len(embeddings)}'
        )

    index_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(index_dir))

    existing_names = {collection.name for collection in client.list_collections()}
    if CHROMA_COLLECTION_NAME in existing_names:
        client.delete_collection(CHROMA_COLLECTION_NAME)

    collection = client.create_collection(name=CHROMA_COLLECTION_NAME)
    total = len(ids)
    for start in range(0, total, CHROMA_INSERT_BATCH_SIZE):
        end = min(start + CHROMA_INSERT_BATCH_SIZE, total)
        collection.add(
            ids=ids[start:end],
            documents=texts[start:end],
            metadatas=metadatas[start:end],
            embeddings=embeddings[start:end],
        )
        print(f'[chroma-progress] stored {end}/{total} records.')

    count = collection.count()
    if count != len(ids):
        raise RuntimeError(
            f'Chroma verification failed: collection.count()={count} expected {len(ids)}'
        )
    print(
        f'Chroma: stored {count} records in {index_dir.resolve()} '
        f'(collection {CHROMA_COLLECTION_NAME!r}).'
    )


def verify_chroma_collection(*, index_dir: Path) -> dict[str, Any]:
    client = chromadb.PersistentClient(path=str(index_dir))
    collection = client.get_collection(CHROMA_COLLECTION_NAME)
    count = collection.count()
    sample = collection.peek(limit=min(3, count))
    sample_ids = sample.get('ids') or []
    sample_metadatas = sample.get('metadatas') or []

    return {
        'count': count,
        'sample_ids': sample_ids,
        'sample_metadatas': sample_metadatas,
    }


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
    limit: int | None = DEFAULT_LIMIT,
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
        total_records = len(records)
        print(f'Starting embedding + Chroma seed for {total_records} records...')
        embeddings = embed_texts(
            texts,
            embedding_model=embedding_model,
            progress_callback=lambda processed, total: print(
                f'[seed-progress] embedded {processed}/{total}'
            ),
        )
        seed_storage(
            index_dir=index_dir,
            ids=ids,
            texts=texts,
            metadatas=metadatas,
            embeddings=embeddings,
        )
        verification = verify_chroma_collection(index_dir=index_dir)
        print(
            'Chroma verification: '
            f"count={verification['count']} sample_ids={verification['sample_ids']}"
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
            message=f'Seed complete: Chroma persisted {len(records)} records with embeddings.',
        )
    except Exception as error:
        return handle_seed_failure(has_existing_manifest=has_existing_manifest, error=error)


def main() -> int:
    parser = ArgumentParser(description='Seed local vector index from parquet dataset.')
    parser.add_argument('--dataset', default=str(DEFAULT_DATASET_PATH))
    parser.add_argument('--index-dir', default=str(DEFAULT_INDEX_DIR))
    parser.add_argument('--embedding-model', default=EMBEDDING_MODEL_ID)
    parser.add_argument(
        '--limit',
        type=int,
        default=DEFAULT_LIMIT,
        help=f'Max records to embed and store (default: {DEFAULT_LIMIT}).',
    )
    parser.add_argument(
        '--no-limit',
        action='store_true',
        help=f'Ingest all records without limiting to {DEFAULT_LIMIT}.',
    )
    args = parser.parse_args()

    status = seed_vector_index(
        dataset_path=Path(args.dataset),
        index_dir=Path(args.index_dir),
        embedding_model=args.embedding_model,
        limit=None if args.no_limit else args.limit,
    )
    print(f'[{status.status}] {status.message}')
    return 0 if status.status in {'seeded', 'skipped', 'warning'} else 1


if __name__ == '__main__':
    raise SystemExit(main())
