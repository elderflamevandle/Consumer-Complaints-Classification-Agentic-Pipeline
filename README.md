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
4. Run baseline checks:
   ```bash
   make test
   make lint
   make typecheck
   ```

## Command Flow

- `make run` - sanity check runtime config load
- `make seed` - build dataset artifacts and seed vector index
- `make eval` - placeholder entrypoint for later evaluation phase
- `make test` - execute unit tests
- `make lint` - run Ruff checks
- `make typecheck` - run mypy against `src/`

## Phase 1 Scope

This baseline intentionally includes only:
- repository structure and settings loader
- Groq client reliability scaffolding
- deterministic dataset + vector-index seed scripts

Higher-level pipeline logic lands in later phases.
