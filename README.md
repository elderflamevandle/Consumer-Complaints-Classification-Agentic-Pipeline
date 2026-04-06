# FinComplaint AI

Phase 1 bootstrap for a deterministic complaint-triage codebase.

## Quickstart

1. Install `uv` (https://docs.astral.sh/uv/)
2. Sync dependencies:
   ```bash
   uv sync
   ```
3. Create environment file:
   ```bash
   cp .env.example .env
   ```
4. Run baseline checks with the cross-platform task runner:
   ```bash
   uv run python scripts/tasks.py test
   uv run python scripts/tasks.py lint
   uv run python scripts/tasks.py typecheck
   ```

Optional Unix shorthand:
```bash
make test
make lint
make typecheck
```

## Command Flow

- `uv run python scripts/tasks.py run` - sanity check runtime config load
- `uv run python scripts/tasks.py seed` - build dataset artifacts and seed vector index
- `uv run python scripts/tasks.py eval` - placeholder entrypoint for later evaluation phase
- `uv run python scripts/tasks.py test` - execute unit tests
- `uv run python scripts/tasks.py lint` - run Ruff checks
- `uv run python scripts/tasks.py typecheck` - run mypy against `src/`

Optional `make` convenience aliases for Unix-like shells:
- `make run`
- `make seed`
- `make eval`
- `make test`
- `make lint`
- `make typecheck`

Dataset build note:
- `uv sync` installs the parquet dependencies (`pandas`, `pyarrow`) required by
  `scripts/build_dataset.py` and `scripts/seed_vectordb.py`.

## Phase 1 Scope

This baseline intentionally includes only:
- repository structure and settings loader
- Groq client reliability scaffolding
- deterministic dataset + vector-index seed scripts

Higher-level pipeline logic lands in later phases.
