"""Hugging Face Inference API feature-extraction (embeddings) with retries."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from os import getenv
from typing import Any

DEFAULT_EMBEDDING_MODEL = 'sentence-transformers/all-MiniLM-L6-v2'
ROUTER_BASE = 'https://router.huggingface.co/hf-inference'
BATCH_SIZE = 100
BATCH_SLEEP_SECONDS = 0.5
MAX_RETRIES_PER_BATCH = 3

ProgressCallback = Callable[[int, int], None]


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(override=True)
    except Exception:
        pass


def _feature_extraction_url(embedding_model: str) -> str:
    return f'{ROUTER_BASE}/models/{embedding_model}/pipeline/feature-extraction'


def _mean_pool_token_embeddings(row: list[Any]) -> list[float]:
    if not row:
        return []

    if all(isinstance(value, (int, float)) for value in row):
        return [float(value) for value in row]

    token_rows = [token for token in row if isinstance(token, list)]
    if not token_rows:
        raise RuntimeError(f'Unexpected embedding row payload: {type(row)}')

    first = token_rows[0]
    if not first or not all(isinstance(value, (int, float)) for value in first):
        raise RuntimeError('Unexpected nested embedding structure returned by Hugging Face API')

    dims = len(first)
    pooled = [0.0] * dims
    count = 0

    for token_row in token_rows:
        if len(token_row) != dims:
            raise RuntimeError('Inconsistent token embedding dimensions returned by Hugging Face API')
        for index, value in enumerate(token_row):
            if not isinstance(value, (int, float)):
                raise RuntimeError('Non-numeric token embedding value returned by Hugging Face API')
            pooled[index] += float(value)
        count += 1

    if count == 0:
        raise RuntimeError('No token embeddings returned by Hugging Face API')

    return [value / count for value in pooled]


def embed_texts(
    texts: list[str],
    *,
    embedding_model: str = DEFAULT_EMBEDDING_MODEL,
    progress_callback: ProgressCallback | None = None,
) -> list[list[float]]:
    """Return one embedding vector per input string via the remote HF inference API."""
    if not texts:
        return []

    _load_dotenv()
    url = _feature_extraction_url(embedding_model)
    headers: dict[str, str] = {'Content-Type': 'application/json'}
    token = getenv('HF_TOKEN')
    if token:
        headers['Authorization'] = f'Bearer {token}'

    all_embeddings: list[list[float]] = []
    total = len(texts)
    print(f'Fetching embeddings from Hugging Face API for {total} texts using {embedding_model}...')

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        batch_queued = False

        for attempt in range(MAX_RETRIES_PER_BATCH):
            payload = json.dumps(
                {
                    'inputs': batch,
                    'options': {'wait_for_model': True},
                }
            ).encode('utf-8')
            req = urllib.request.Request(url, data=payload, headers=headers, method='POST')
            try:
                with urllib.request.urlopen(req, timeout=120) as response:
                    result: Any = json.loads(response.read().decode('utf-8'))
            except urllib.error.HTTPError as e:
                try:
                    error_body = e.read().decode('utf-8')
                except Exception:
                    error_body = str(e)
                if 'loading' in error_body.lower():
                    try:
                        err_data = json.loads(error_body)
                        wait_time = int(err_data.get('estimated_time', 10))
                    except Exception:
                        wait_time = 10
                    print(f'Model is loading, waiting {wait_time}s...')
                    time.sleep(wait_time)
                    continue
                raise RuntimeError(
                    f'HF embedding HTTP {e.code}: {error_body[:800]}'
                ) from e
            except Exception as e:
                if attempt + 1 >= MAX_RETRIES_PER_BATCH:
                    raise RuntimeError(
                        f'HF embedding failed for batch at index {i}: {e}'
                    ) from e
                time.sleep(2.0)
                continue

            if isinstance(result, dict) and 'error' in result:
                err_msg = str(result.get('error', ''))
                if 'loading' in err_msg.lower():
                    wait_time = int(result.get('estimated_time', 10))
                    print(f'Model is loading, waiting {wait_time}s...')
                    time.sleep(wait_time)
                    continue
                raise RuntimeError(f'HF API error: {result}')

            if not isinstance(result, list):
                raise RuntimeError(f'Unexpected response format (expected list): {type(result)}')

            normalized: list[list[float]] = []
            for row in result:
                if not isinstance(row, list):
                    raise RuntimeError(f'Expected list rows from HF API, got row type {type(row)}')
                normalized.append(_mean_pool_token_embeddings(row))

            if len(normalized) != len(batch):
                raise RuntimeError(
                    f'Batch size mismatch: API returned {len(normalized)} vectors '
                    f'for {len(batch)} texts'
                )

            all_embeddings.extend(normalized)
            processed = min(len(all_embeddings), total)
            if progress_callback is not None:
                progress_callback(processed, total)
            print(f'Embedding progress: {processed}/{total} records processed.')
            batch_queued = True
            break

        if not batch_queued:
            raise RuntimeError(
                f'HF embedding exhausted retries for batch at index {i} '
                f'({len(batch)} texts)'
            )

        time.sleep(BATCH_SLEEP_SECONDS)

    if len(all_embeddings) != len(texts):
        raise RuntimeError(
            f'Embedding count mismatch: got {len(all_embeddings)} vectors for {len(texts)} texts'
        )
    return all_embeddings
