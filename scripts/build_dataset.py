"""Build deterministic CFPB sample artifacts with a fixed split contract."""

from __future__ import annotations

import csv
import json
import random
import re
from argparse import ArgumentParser
from collections import defaultdict
from pathlib import Path
from typing import Iterable

from src.config import get_settings

TARGET_SIZE = 10_000
DEV_SIZE = 7_000
HOLDOUT_SIZE = 2_000
DEMO_SIZE = 1_000


def is_english_text(text: str, threshold: float = 0.85) -> bool:
    if not text:
        return False
    ascii_like = sum(1 for char in text if ord(char) < 128)
    return (ascii_like / len(text)) >= threshold


def apply_filters(
    records: Iterable[dict[str, str]],
    *,
    min_length: int = 40,
) -> list[dict[str, str]]:
    filtered: list[dict[str, str]] = []
    for record in records:
        narrative = record.get('narrative', '').strip()
        if not narrative or len(narrative) < min_length:
            continue
        if not is_english_text(narrative):
            continue
        filtered.append(record)
    return filtered


def _group_key(record: dict[str, str]) -> tuple[str, str]:
    return (record.get('product', 'unknown'), record.get('issue', 'unknown'))


def _compute_quotas(
    groups: dict[tuple[str, str], list[dict[str, str]]],
    *,
    target_size: int,
) -> dict[tuple[str, str], int]:
    total = sum(len(items) for items in groups.values())
    if total < target_size:
        raise ValueError(
            'Not enough records after filtering for requested sample size: '
            f'need {target_size}, found {total}. '
            'If you are using the official CFPB export, make sure the narrative column '
            'is being read correctly.'
        )

    floor_allocations: dict[tuple[str, str], int] = {}
    remainders: list[tuple[float, tuple[str, str]]] = []

    for key, items in groups.items():
        exact = (len(items) / total) * target_size
        floor_value = min(len(items), int(exact))
        floor_allocations[key] = floor_value
        remainders.append((exact - floor_value, key))

    assigned = sum(floor_allocations.values())
    remaining = target_size - assigned

    for _, key in sorted(remainders, reverse=True):
        if remaining == 0:
            break
        if floor_allocations[key] < len(groups[key]):
            floor_allocations[key] += 1
            remaining -= 1

    if remaining > 0:
        for key in sorted(groups):
            if remaining == 0:
                break
            capacity = len(groups[key]) - floor_allocations[key]
            if capacity <= 0:
                continue
            take = min(capacity, remaining)
            floor_allocations[key] += take
            remaining -= take

    if remaining != 0:
        raise RuntimeError('Unable to satisfy stratified quota assignment')
    return floor_allocations


def stratified_sample(
    records: list[dict[str, str]],
    *,
    target_size: int = TARGET_SIZE,
    seed: int = 42,
) -> list[dict[str, str]]:
    groups: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for record in records:
        groups[_group_key(record)].append(record)

    quotas = _compute_quotas(groups, target_size=target_size)
    sample: list[dict[str, str]] = []

    for key in sorted(groups):
        bucket = list(groups[key])
        rng = random.Random(f'{seed}:{key[0]}:{key[1]}')
        rng.shuffle(bucket)
        sample.extend(bucket[: quotas[key]])

    ordered = sorted(sample, key=lambda r: r.get('id', ''))
    random.Random(seed).shuffle(ordered)
    return ordered


def split_sample(
    sample: list[dict[str, str]],
    *,
    seed: int,
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    if len(sample) != TARGET_SIZE:
        raise ValueError(f'sample must contain exactly {TARGET_SIZE} records')

    shuffled = list(sample)
    random.Random(seed).shuffle(shuffled)

    dev = shuffled[:DEV_SIZE]
    holdout = shuffled[DEV_SIZE : DEV_SIZE + HOLDOUT_SIZE]
    demos = shuffled[DEV_SIZE + HOLDOUT_SIZE :]
    return dev, holdout, demos


def _load_csv_records(input_path: Path) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    with input_path.open('r', encoding='utf-8', newline='') as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            normalized = _normalize_row_keys(row)
            records.append(
                {
                    'id': (
                        normalized.get('complaint_id')
                        or normalized.get('id')
                        or str(len(records))
                    ),
                    'product': normalized.get('product') or '',
                    'issue': normalized.get('issue') or '',
                    'narrative': (
                        normalized.get('consumer_complaint_narrative')
                        or normalized.get('narrative')
                        or ''
                    ),
                    'state': normalized.get('state') or '',
                    'date': normalized.get('date_received') or normalized.get('date') or '',
                }
            )
    return records


def _normalize_row_keys(row: dict[str | None, str | None]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key, value in row.items():
        if key is None:
            continue
        token = _normalize_header_name(key)
        if token and token not in normalized:
            normalized[token] = value or ''
    return normalized


def _normalize_header_name(name: str) -> str:
    token = name.strip().lower()
    token = re.sub(r'[^a-z0-9]+', '_', token)
    return token.strip('_')


def _write_parquet(records: list[dict[str, str]], output_path: Path) -> None:
    try:
        import pandas as pd
    except Exception as error:
        raise RuntimeError('pandas + pyarrow are required to write parquet artifacts') from error

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(records).to_parquet(output_path, index=False)


def build_dataset(
    *,
    input_path: Path,
    output_dir: Path,
    seed: int,
) -> dict[str, object]:
    source_records = _load_csv_records(input_path)
    filtered = apply_filters(source_records)
    sample = stratified_sample(filtered, target_size=TARGET_SIZE, seed=seed)
    dev, holdout, demos = split_sample(sample, seed=seed)

    dev_path = output_dir / 'dev.parquet'
    holdout_path = output_dir / 'holdout.parquet'
    demos_path = output_dir / 'demos.parquet'

    _write_parquet(dev, dev_path)
    _write_parquet(holdout, holdout_path)
    _write_parquet(demos, demos_path)

    metadata = {
        'seed': seed,
        'source_records': len(source_records),
        'filtered_records': len(filtered),
        'sample_size': len(sample),
        'split': {'dev': len(dev), 'holdout': len(holdout), 'demos': len(demos)},
        'artifacts': {
            'dev_parquet': str(dev_path),
            'holdout_parquet': str(holdout_path),
            'demos_parquet': str(demos_path),
        },
    }
    metadata_path = output_dir / 'metadata.json'
    metadata_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True),
        encoding='utf-8',
    )
    return metadata


def main() -> int:
    parser = ArgumentParser(description='Build deterministic CFPB dataset artifacts.')
    parser.add_argument('--input', required=True, help='Path to CFPB CSV export')
    parser.add_argument('--output-dir', default='data/processed', help='Output directory')
    parser.add_argument('--seed', type=int, default=get_settings().dataset_seed)
    args = parser.parse_args()

    metadata = build_dataset(
        input_path=Path(args.input),
        output_dir=Path(args.output_dir),
        seed=args.seed,
    )
    print(json.dumps(metadata, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
