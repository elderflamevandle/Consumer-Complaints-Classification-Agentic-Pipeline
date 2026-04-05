---
phase: 01-foundation-and-runtime-baseline
plan: "03"
subsystem: data
tags: [dataset, parquet, chroma, embeddings, stale-detection, hashing]
requires:
  - phase: 01-01
    provides: Shared runtime setup and execution commands
provides:
  - Deterministic CFPB sampling with fixed 7k/2k/1k split contract
  - Hash-based vector index stale detection using dataset_hash + embedding model
  - Seeding workflow with warning mode that preserves prior index on refresh failure
affects: [phase-03-rag, phase-05-ui-demos, phase-06-eval]
tech-stack:
  added: [parquet artifacts, local manifest contract, optional chromadb persistence]
  patterns: [manifest-first stale check, deterministic fallback embedding path]
key-files:
  created:
    - scripts/build_dataset.py
    - scripts/seed_vectordb.py
    - src/tools/vector_index.py
    - tests/test_data_pipeline.py
    - data/README.md
  modified: []
key-decisions:
  - "Used deterministic quota-based stratified sampling to maintain reproducibility across machines."
  - "Kept seed failure behavior warning-compatible so startup can continue with last valid index."
patterns-established:
  - "Pattern: index refresh is gated strictly by dataset_hash and embedding_model changes."
  - "Pattern: data contracts are validated through focused split and stale-detection regression tests."
requirements-completed: [DATA-01, DATA-02]
duration: 47min
completed: 2026-04-05
---

# Phase 1 Plan 03 Summary

**Delivered deterministic data preparation and stale-aware vector seeding contracts required for downstream retrieval and evaluation phases.**

## Performance

- **Duration:** 47 min
- **Started:** 2026-04-05T13:38:00-04:00
- **Completed:** 2026-04-05T14:25:00-04:00
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments
- Implemented reproducible CFPB sampling with filters and fixed split outputs (`dev/holdout/demos` parquet).
- Implemented vector seeding pipeline with dataset hash + embedding model stale detection.
- Added regression coverage for split determinism, stale triggers, and failure fallback behavior.

## Task Commits

Each task was committed atomically:

1. **Task 1: Build deterministic CFPB sampling script with fixed split contract** - `42c0258` (feat)
2. **Task 2: Implement vector seeding with hash-based stale detection** - `158382f` (feat)
3. **Task 3: Add data pipeline regression tests and seed manifest checks** - `4bb583c` (test)

## Files Created/Modified
- `scripts/build_dataset.py` - Filtering, stratified sampling, deterministic split, and parquet/metadata output flow.
- `scripts/seed_vectordb.py` - Vector seed orchestration with stale checks and warning-compatible failure handling.
- `src/tools/vector_index.py` - Manifest schema, dataset hash helpers, and stale detection primitives.
- `tests/test_data_pipeline.py` - Regression tests for split determinism and stale-trigger correctness.
- `data/README.md` - Artifact contract and rerun instructions.

## Decisions Made
- Selected manifest-based stale checks instead of timestamp-based checks to avoid unnecessary rebuild churn.
- Added deterministic hash-vector embedding fallback when sentence-transformer weights are unavailable locally.

## Deviations from Plan

None - plan executed as written.

## Issues Encountered
- Initial Ruff check flagged import ordering and line length in new scripts; corrected with formatting and targeted wrapping.

## User Setup Required

External/local setup required for full data seeding runs:
- Provide CFPB CSV input for `scripts/build_dataset.py --input <path>`.
- Install optional heavy deps (`pandas`, `pyarrow`, `chromadb`, `sentence-transformers`) for full parquet + chroma execution paths.

## Next Phase Readiness
- Retrieval-oriented phases can rely on explicit stale detection and manifest metadata.
- Data artifacts and test contracts are now deterministic and repeatable.

---
*Phase: 01-foundation-and-runtime-baseline*
*Completed: 2026-04-05*