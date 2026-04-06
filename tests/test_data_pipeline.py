from __future__ import annotations

from pathlib import Path

from scripts.build_dataset import _load_csv_records, apply_filters, split_sample, stratified_sample
from scripts.seed_vectordb import EMBEDDING_MODEL_ID, handle_seed_failure
from src.tools.vector_index import (
    compute_dataset_hash,
    create_manifest,
    should_reseed,
    write_manifest,
)


def _synthetic_record(index: int) -> dict[str, str]:
    return {
        'id': str(index),
        'product': 'credit_card' if index % 2 == 0 else 'bank_account',
        'issue': 'billing' if index % 3 == 0 else 'fraud',
        'narrative': (
            f'Customer complaint narrative {index} '
            'with enough english words for filtering.'
        ),
        'state': 'CA' if index % 2 == 0 else 'NY',
        'date': f'2025-01-{(index % 28) + 1:02d}',
    }


def test_sampling_split() -> None:
    records = [_synthetic_record(i) for i in range(12_000)]
    filtered = apply_filters(records, min_length=20)

    sample_a = stratified_sample(filtered, target_size=10_000, seed=42)
    sample_b = stratified_sample(filtered, target_size=10_000, seed=42)

    assert [row['id'] for row in sample_a] == [row['id'] for row in sample_b]

    dev, holdout, demos = split_sample(sample_a, seed=42)
    assert len(dev) == 7_000
    assert len(holdout) == 2_000
    assert len(demos) == 1_000


def test_load_csv_records_supports_official_cfpb_headers(tmp_path: Path) -> None:
    csv_path = tmp_path / 'complaints.csv'
    csv_path.write_text(
        (
            'Date received,Product,Issue,Consumer complaint narrative,State,Complaint ID\n'
            '2025-01-01,Credit card,Billing,'
            'This is a detailed complaint narrative for testing,CA,12345\n'
        ),
        encoding='utf-8',
    )

    records = _load_csv_records(csv_path)

    assert len(records) == 1
    assert records[0]['id'] == '12345'
    assert records[0]['product'] == 'Credit card'
    assert records[0]['issue'] == 'Billing'
    assert records[0]['narrative'] == 'This is a detailed complaint narrative for testing'
    assert records[0]['state'] == 'CA'
    assert records[0]['date'] == '2025-01-01'


def test_stale_detection(tmp_path: Path) -> None:
    dataset_path = tmp_path / 'dev.parquet'
    dataset_path.write_bytes(b'parquet-binary-content')
    dataset_hash = compute_dataset_hash(dataset_path)
    index_dir = tmp_path / 'chroma_db'

    stale, reason = should_reseed(
        index_dir=index_dir,
        dataset_hash=dataset_hash,
        embedding_model=EMBEDDING_MODEL_ID,
    )
    assert stale is True
    assert reason == 'manifest_missing'

    manifest = create_manifest(
        dataset_hash=dataset_hash,
        embedding_model=EMBEDDING_MODEL_ID,
        dataset_path=dataset_path,
        index_path=index_dir,
        record_count=5000,
    )
    write_manifest(index_dir, manifest)

    stale, reason = should_reseed(
        index_dir=index_dir,
        dataset_hash=dataset_hash,
        embedding_model=EMBEDDING_MODEL_ID,
    )
    assert stale is False
    assert reason == 'fresh'

    stale, reason = should_reseed(
        index_dir=index_dir,
        dataset_hash=dataset_hash,
        embedding_model='different-model',
    )
    assert stale is True
    assert reason == 'embedding_model_changed'

    dataset_path.write_bytes(b'changed-parquet-binary-content')
    changed_hash = compute_dataset_hash(dataset_path)
    stale, reason = should_reseed(
        index_dir=index_dir,
        dataset_hash=changed_hash,
        embedding_model=EMBEDDING_MODEL_ID,
    )
    assert stale is True
    assert reason == 'dataset_hash_changed'


def test_failure_can_keep_last_valid_index() -> None:
    status = handle_seed_failure(
        has_existing_manifest=True,
        error=RuntimeError('embedding service unavailable'),
    )
    assert status.status == 'warning'
    assert status.reused_previous_index is True
