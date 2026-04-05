# Data Artifacts

Phase 1 data outputs are deterministic and tied to a fixed split contract.

## Expected Artifacts

- `processed/dev.parquet` - 7,000 records
- `processed/holdout.parquet` - 2,000 records
- `processed/demos.parquet` - 1,000 records
- `processed/metadata.json` - seed, filter counts, and split metadata

## Rebuild Steps

1. Build dataset sample and parquet outputs:
   - `uv run python scripts/build_dataset.py --input <cfpb_csv_path>`
2. Seed local vector index from `dev.parquet`:
   - `uv run python scripts/seed_vectordb.py`

Vector seeding rebuilds only when dataset hash or embedding model changes.
Current embedding model contract: `bge-large-en-v1.5`.