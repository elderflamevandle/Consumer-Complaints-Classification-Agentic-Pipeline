"""Manifest and stale-check utilities for local vector index artifacts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

MANIFEST_FILENAME = 'manifest.json'


@dataclass(frozen=True)
class IndexManifest:
    dataset_hash: str
    embedding_model: str
    dataset_path: str
    index_path: str
    record_count: int
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            'dataset_hash': self.dataset_hash,
            'embedding_model': self.embedding_model,
            'dataset_path': self.dataset_path,
            'index_path': self.index_path,
            'record_count': self.record_count,
            'created_at': self.created_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> 'IndexManifest':
        return cls(
            dataset_hash=str(payload['dataset_hash']),
            embedding_model=str(payload['embedding_model']),
            dataset_path=str(payload['dataset_path']),
            index_path=str(payload['index_path']),
            record_count=int(payload['record_count']),
            created_at=str(payload['created_at']),
        )


def compute_dataset_hash(dataset_path: Path) -> str:
    digest = hashlib.sha256()
    with dataset_path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(8192), b''):
            digest.update(chunk)
    return digest.hexdigest()


def manifest_path_for(index_dir: Path) -> Path:
    return index_dir / MANIFEST_FILENAME


def read_manifest(index_dir: Path) -> IndexManifest | None:
    path = manifest_path_for(index_dir)
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(payload, dict):
        return None
    return IndexManifest.from_dict(payload)


def write_manifest(index_dir: Path, manifest: IndexManifest) -> Path:
    index_dir.mkdir(parents=True, exist_ok=True)
    path = manifest_path_for(index_dir)
    path.write_text(
        json.dumps(manifest.to_dict(), indent=2, sort_keys=True),
        encoding='utf-8',
    )
    return path


def create_manifest(
    *,
    dataset_hash: str,
    embedding_model: str,
    dataset_path: Path,
    index_path: Path,
    record_count: int,
) -> IndexManifest:
    return IndexManifest(
        dataset_hash=dataset_hash,
        embedding_model=embedding_model,
        dataset_path=str(dataset_path),
        index_path=str(index_path),
        record_count=record_count,
        created_at=datetime.now(UTC).isoformat(),
    )


def is_stale(
    manifest: IndexManifest,
    *,
    dataset_hash: str,
    embedding_model: str,
) -> bool:
    return (
        manifest.dataset_hash != dataset_hash
        or manifest.embedding_model != embedding_model
    )


def should_reseed(
    *,
    index_dir: Path,
    dataset_hash: str,
    embedding_model: str,
) -> tuple[bool, str]:
    manifest = read_manifest(index_dir)
    if manifest is None:
        return True, 'manifest_missing'
    if manifest.dataset_hash != dataset_hash:
        return True, 'dataset_hash_changed'
    if manifest.embedding_model != embedding_model:
        return True, 'embedding_model_changed'
    return False, 'fresh'