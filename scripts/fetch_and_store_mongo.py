"""Fetch complaint data from a remote API and store it in MongoDB."""

from __future__ import annotations

from argparse import ArgumentParser
from typing import Any

from src.tools.consumer_complaints_api import fetch_complaint_records
from src.tools.mongo_client import (
    bulk_upsert_documents,
    get_collection,
    get_mongo_database,
)


def parse_query_pairs(pairs: list[str]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for pair in pairs:
        if '=' not in pair:
            raise ValueError('Query parameters must be passed as key=value pairs.')
        key, value = pair.split('=', 1)
        parsed[key.strip()] = value.strip()
    return parsed


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description='Fetch complaint records from an API and ingest them into MongoDB.'
    )
    parser.add_argument(
        '--api-url',
        default='https://www.consumerfinance.gov/data-research/consumer-complaints/search/api/v1/',
        help='Consumer complaint API base URL.',
    )
    parser.add_argument(
        '--mongo-uri',
        default=None,
        help='MongoDB connection string. Falls back to MONGO_URI.',
    )
    parser.add_argument(
        '--mongo-db',
        default=None,
        help='MongoDB database name. Falls back to MONGO_DATABASE.',
    )
    parser.add_argument(
        '--collection',
        default='complaints',
        help='MongoDB collection name to write documents to.',
    )
    parser.add_argument(
        '--page-size',
        type=int,
        default=100,
        help='Number of records to request per page from the remote API.',
    )
    parser.add_argument(
        '--max-pages',
        type=int,
        default=5,
        help='Maximum number of pages to fetch from the remote API.',
    )
    parser.add_argument(
        '--query',
        action='append',
        default=[],
        help='Optional query parameters for the API, specified as key=value.',
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    query_params = parse_query_pairs(args.query)
    database = get_mongo_database(mongo_uri=args.mongo_uri, database_name=args.mongo_db)
    collection = get_collection(database, args.collection)

    records = fetch_complaint_records(
        api_url=args.api_url,
        page_size=args.page_size,
        max_pages=args.max_pages,
        query_params=query_params,
    )

    if not records:
        print('No records were downloaded from the remote API.')
        return 1

    updated = bulk_upsert_documents(collection, records)
    print(f'Inserted or updated {updated} complaint documents into MongoDB.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
