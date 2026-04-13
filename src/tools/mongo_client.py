"""MongoDB helper utilities for consumer complaint ingestion."""

from __future__ import annotations

from typing import Any

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from src.config import get_settings


def get_mongo_client(mongo_uri: str | None = None) -> MongoClient:
    settings = get_settings()
    uri = mongo_uri or settings.mongo_uri
    if not uri:
        raise RuntimeError(
            'MongoDB ingestion requires MONGO_URI environment variable or explicit URI.'
        )
    return MongoClient(uri, serverSelectionTimeoutMS=5000)


def get_mongo_database(
    *,
    mongo_uri: str | None = None,
    database_name: str | None = None,
) -> Database:
    settings = get_settings()
    db_name = database_name or settings.mongo_database
    if not db_name:
        raise RuntimeError(
            'MongoDB ingestion requires MONGO_DATABASE environment variable or explicit database name.'
        )
    client = get_mongo_client(mongo_uri)
    return client[db_name]


def get_collection(
    database: Database,
    collection_name: str = 'complaints',
) -> Collection:
    return database[collection_name]


def _normalize_record_for_storage(record: dict[str, Any]) -> dict[str, Any]:
    document = dict(record)
    complaint_id = document.get('complaint_id') or document.get('id') or document.get('_id')
    if complaint_id is None:
        raise ValueError('Complaint record is missing a stable complaint identifier.')

    complaint_id = str(complaint_id).strip()
    if not complaint_id:
        raise ValueError('Complaint record is missing a stable complaint identifier.')

    document['_id'] = complaint_id
    return document


def bulk_upsert_documents(
    collection: Collection,
    records: list[dict[str, Any]],
) -> int:
    if not records:
        return 0

    try:
        from pymongo import UpdateOne
    except ImportError as error:
        raise RuntimeError('pymongo is required for MongoDB ingestion.') from error

    operations = []
    for record in records:
        normalized = _normalize_record_for_storage(record)
        operations.append(
            UpdateOne(
                {'_id': normalized['_id']},
                {'$set': normalized},
                upsert=True,
            )
        )

    if not operations:
        return 0

    result = collection.bulk_write(operations, ordered=False)
    return int(result.upserted_count + result.modified_count)
