# Phase 1: Foundation and Runtime Baseline - Research

**Researched:** 2026-04-05
**Domain:** Python agentic workflow bootstrap (Groq + dataset sampling + vector seeding)
**Confidence:** MEDIUM

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Use `uv` with `pyproject.toml` for environment and dependency management.
- Create modular structure from day one (`src/`, `app/`, `scripts/`, `tests/`).
- Standardize commands through `Makefile` (`run`, `seed`, `eval`, `test`).
- Enforce baseline quality tooling with `pytest`, `ruff`, and lightweight `mypy`.
- CFPB sample strategy: stratified by product + issue, filtered (non-empty, min length, English-only), split `7k dev + 2k holdout + 1k demos`.
- Chroma seeding uses `bge-large-en-v1.5`, persisted local index, refresh only when missing/stale.
- Stale detection is dataset-hash + embedding-model-id.
- Startup seeding failure should continue using last valid index with warning.
- Groq retry policy: 3 retries exponential backoff.
- Groq timeout policy: 45s per call.
- Fallback triggers: 429, timeout, transient 5xx.
- Budget pressure behavior: warn + degrade non-critical 70B calls.
- Groq provider for v1 with fallback chain fixed as `llama-3.3-70b-versatile -> mixtral-8x7b-32768 -> llama-3.1-8b-instant`.

### Claude's Discretion
- Exact module/file names inside the agreed directory structure.
- Exact linter/type-check strictness thresholds.
- Logging field format for retries, fallback events, and budget warnings.

### Deferred Ideas (OUT OF SCOPE)
- None.

</user_constraints>

<research_summary>
## Summary

Phase 1 should prioritize deterministic scaffolding and reliability primitives, not feature breadth. The implementation should create a stable local developer path (`uv sync`, repeatable scripts, clear Make targets), a resilient Groq client with explicit fallback behavior, and reproducible data artifacts for downstream phases.

The most important quality lever is determinism: version-pinned dependencies, hash-based artifact freshness checks, strict model-routing rules, and repeatable dataset generation. This keeps future phases focused on capability building instead of rework caused by unstable foundations.

**Primary recommendation:** implement Phase 1 as three vertically coherent plans: foundation bootstrap, Groq reliability module, and deterministic data/seed pipeline.
</research_summary>

<standard_stack>
## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| python | 3.11+ | Runtime | Stable ecosystem for LangGraph/data tooling and modern typing |
| uv | latest stable | Env + dependency management | Fast, lockable workflow for one-command setup |
| pydantic | >=2.7 | Runtime validation | Keeps config and structured outputs deterministic |
| openai sdk | >=1.50 | Groq-compatible client transport | Unified client abstraction + JSON mode support |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | >=8 | Testing baseline | All module-level and regression tests |
| ruff | >=0.6 | Lint + format checks | Fast CI/local hygiene with low overhead |
| mypy | >=1.10 | Type sanity checks | Lightweight static validation for public interfaces |
| pandas + pyarrow | >=2.2 / >=17 | Dataset transform + parquet | Reproducible sampling output |
| chromadb | >=0.5 | Local vector store | Persisted retrieval index for root-cause stage |
| sentence-transformers | >=3.0 | Embeddings | `bge-large-en-v1.5` generation in offline script |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| uv | pip + requirements.txt | More familiar but weaker lock/repro ergonomics |
| openai sdk (Groq base_url) | native groq sdk | Slightly cleaner provider semantics, less portable interface |
| local Chroma | managed vector DB | Better scale, unnecessary complexity/cost in week one |

**Installation:**
```bash
uv sync
uv run python -m pytest -q
```
</standard_stack>

<architecture_patterns>
## Architecture Patterns

### Recommended Project Structure
```
src/
|-- llm/           # client, model registry, retry/fallback, budget tracking
|-- schemas/       # pydantic contracts
|-- tools/         # vector index helpers and utility abstractions
|-- config.py      # settings loader
scripts/
|-- build_dataset.py
`-- seed_vectordb.py
tests/
`-- module-focused test files
```

### Pattern 1: Policy-Driven Model Routing
**What:** Keep fallback and trigger rules centralized in one module.
**When to use:** Multi-model provider flows with explicit reliability behavior.
**Example:**
```python
FALLBACK_CHAIN = [
    "llama-3.3-70b-versatile",
    "mixtral-8x7b-32768",
    "llama-3.1-8b-instant",
]
```

### Pattern 2: Hash-Gated Artifact Regeneration
**What:** Recompute expensive artifacts only when source inputs or model identity change.
**When to use:** Startup paths that need fast boot and deterministic refresh behavior.
**Example:**
```python
stale = (manifest.dataset_hash != current_dataset_hash) or (manifest.embedding_model != model_name)
```

### Anti-Patterns to Avoid
- Rebuilding embeddings on every startup.
- Spreading fallback logic across multiple agent files.
- Leaving sampling randomness unseeded.
</architecture_patterns>

<dont_hand_roll>
## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Retry/backoff state machine | custom scattered retry code in agents | centralized client wrapper | avoids inconsistency and hard-to-debug failure paths |
| Data partitioning logic from scratch in many scripts | ad hoc split code per script | one deterministic sampling script | prevents split drift across runs |
| Vector metadata/version tracking as manual notes | undocumented ad hoc changes | manifest file with hashes/model id | reproducible and automatable refresh decisions |

**Key insight:** foundation phase quality comes from repeatability contracts, not algorithm novelty.
</dont_hand_roll>

<common_pitfalls>
## Common Pitfalls

### Pitfall 1: Fallback chain drift
**What goes wrong:** Different modules use inconsistent model names and trigger rules.
**Why it happens:** Logic duplicated in multiple files.
**How to avoid:** Single model-routing registry and shared fallback helper.
**Warning signs:** Tests pass in one path but runtime fails in another.

### Pitfall 2: Non-reproducible dataset outputs
**What goes wrong:** Team members get different samples/splits from same script.
**Why it happens:** Missing fixed seed and undocumented filters.
**How to avoid:** Hardcode seed + filter configuration and output metadata.
**Warning signs:** Eval metrics vary heavily across local machines.

### Pitfall 3: Expensive startup regressions
**What goes wrong:** Application startup triggers full embedding rebuild too often.
**Why it happens:** No stale-check contract.
**How to avoid:** Compare dataset hash + model ID before rebuild.
**Warning signs:** First-run latency appears on every run.
</common_pitfalls>

<code_examples>
## Code Examples

### Groq client retry + fallback skeleton
```python
for model in FALLBACK_CHAIN:
    for attempt in range(max_retries):
        try:
            return call_model(model)
        except RateLimitError:
            sleep(2 ** attempt)
            continue
        except (TimeoutError, TransientServerError):
            if attempt == max_retries - 1:
                break
```

### Deterministic split skeleton
```python
rng = np.random.default_rng(seed=42)
shuffled = df.sample(frac=1.0, random_state=42)
dev, holdout, demos = np.split(shuffled, [7000, 9000])
```

### Stale manifest check
```python
manifest = load_manifest(path)
if manifest.dataset_hash != current_hash or manifest.embedding_model != model_name:
    rebuild_index()
```
</code_examples>

<sota_updates>
## State of the Art (2024-2025)

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| pip-only env bootstrap | uv-first workflows | 2024 adoption surge | faster sync and cleaner lock behavior |
| implicit model fallback assumptions | explicit provider-specific fallback registries | 2024-2025 reliability trend | fewer runtime surprises |
| always-refresh local vector indexes | hash-driven refresh gates | 2024 pragmatic ops pattern | major startup stability gains |

**New tools/patterns to consider:**
- `ruff format` + lint in one toolchain for fast local hygiene.
- Manifest-driven artifact metadata for deterministic build pipelines.

**Deprecated/outdated:**
- Rebuilding expensive assets without change detection.
</sota_updates>

## Validation Architecture

Phase 1 validation should enforce fast feedback:
- Quick loop: `uv run pytest -q tests/test_smoke.py tests/test_llm_client.py`
- Full loop: `uv run pytest -q && uv run ruff check . && uv run mypy src`
- Every plan must include at least one automated verification command.

Planned verification focus:
1. Setup reproducibility and bootstrap commands.
2. Fallback/retry behavior under simulated trigger classes.
3. Sampling + stale detection determinism.

<open_questions>
## Open Questions

1. **Dataset source schema stability**
   - What we know: sampling pipeline assumes stable CFPB fields.
   - What's unclear: potential field drift in upstream dataset snapshots.
   - Recommendation: include schema assertion + fail-fast message in script.

2. **Embedding model runtime constraints**
   - What we know: `bge-large-en-v1.5` is heavier than MiniLM.
   - What's unclear: exact machine constraints in all demo environments.
   - Recommendation: keep explicit warning + runtime telemetry in seed script.
</open_questions>

<sources>
## Sources

### Primary (HIGH confidence)
- `.planning/phases/01-foundation-and-runtime-baseline/01-CONTEXT.md`
- `.planning/ROADMAP.md`
- `.planning/REQUIREMENTS.md`

### Secondary (MEDIUM confidence)
- `.planning/research/SUMMARY.md`
- `plan2.md`

### Tertiary (LOW confidence - needs validation)
- None.
</sources>

<metadata>
## Metadata

**Research scope:**
- Core technology: Python + Groq client reliability + deterministic data tooling
- Ecosystem: uv, pytest, ruff, mypy, pandas, chromadb, sentence-transformers
- Patterns: fallback policy, artifact hashing, reproducible splits
- Pitfalls: fallback drift, split nondeterminism, startup rebuild regressions

**Confidence breakdown:**
- Standard stack: MEDIUM - based on project context and current conventions
- Architecture: MEDIUM - strong internal fit with current roadmap
- Pitfalls: HIGH - derived from known reliability failure modes
- Code examples: MEDIUM - pattern-level templates, not copy-paste from provider docs

**Research date:** 2026-04-05
**Valid until:** 2026-05-05
</metadata>

---

*Phase: 01-foundation-and-runtime-baseline*
*Research completed: 2026-04-05*
*Ready for planning: yes*
