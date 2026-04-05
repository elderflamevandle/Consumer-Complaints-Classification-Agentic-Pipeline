# Phase 1: Foundation and Runtime Baseline - Research

**Researched:** 2026-04-05
**Domain:** Foundation setup for Python-based agentic pipeline (bootstrap, client reliability, deterministic data artifacts)
**Confidence:** MEDIUM

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Use `uv` + `pyproject.toml` for environment and dependency management.
- Create modular structure from day one (`src/`, `app/`, `scripts/`, `tests/`).
- Standardize commands through `Makefile` (`run`, `seed`, `eval`, `test`).
- Enforce baseline quality tooling with `pytest`, `ruff`, and lightweight `mypy` checks.
- CFPB sample strategy: stratified by product + issue, filtered (non-empty, min length, English-only), split `7k dev + 2k holdout + 1k demos`.
- Chroma seeding uses `bge-large-en-v1.5` and persists a local index.
- Rebuild index only when missing or stale.
- Stale detection must use dataset hash + embedding model id.
- On startup seeding failure, continue with last valid index and warn.
- Groq client policy: 3 retries (exponential backoff), 45s timeout.
- Fallback triggers: 429, timeout, transient 5xx.
- Budget policy: warn + degrade non-critical 70B usage.
- Fallback chain fixed: `llama-3.3-70b-versatile -> mixtral-8x7b-32768 -> llama-3.1-8b-instant`.

### Claude's Discretion
- Exact internal module/file naming within the agreed structure.
- Exact lint/type strictness levels.
- Logging field formats for retries, fallback, and budget events.

### Deferred Ideas (OUT OF SCOPE)
- None.

</user_constraints>

<research_summary>
## Summary

Phase 1 should optimize for deterministic execution and low rework in later phases. The highest-value outcomes are: reproducible bootstrap, centralized model-routing reliability, and reproducible dataset/index artifacts that downstream phases can trust.

For this phase, avoid capability expansion and keep implementation focused on contracts that preserve consistency: one source of truth for fallback/routing, one source of truth for sampling and partitioning, and one source of truth for stale-index decisions.

**Primary recommendation:** keep the current three-plan structure (bootstrap, reliability client, data/index pipeline), and tighten verification around deterministic outputs.
</research_summary>

<standard_stack>
## Standard Stack

### Core
| Library | Purpose | Why Standard for this phase |
|---------|---------|-----------------------------|
| Python 3.11+ | Runtime | Stable typing/tooling support and ecosystem fit |
| uv | Environment and dependency workflow | Fast, reproducible setup experience |
| Pydantic | Config and structured data contracts | Deterministic validation of IO/config |
| OpenAI-compatible client transport for Groq | LLM API wrapper | Centralized model routing and retry policy |

### Supporting
| Library | Purpose | When to Use |
|---------|---------|-------------|
| pytest | Automated checks | Unit and deterministic contract tests |
| ruff | Lint and formatting policy | Fast baseline quality gate |
| mypy | Type sanity checks | Public interfaces and client contracts |
| pandas + pyarrow | Sampling and parquet artifacts | Deterministic dataset pipeline outputs |
| chromadb | Local vector index | Local persisted retrieval baseline |
| sentence-transformers | Embeddings (`bge-large-en-v1.5`) | Offline index generation |

### Alternatives Considered
| Standard Choice | Alternative | Tradeoff |
|-----------------|-------------|----------|
| uv workflow | venv + pip + requirements | simpler familiarity vs weaker reproducibility ergonomics |
| centralized client policy module | per-agent fallback handling | less coupling vs higher drift risk |
| local Chroma persistence | hosted vector service | scale headroom vs extra complexity/cost |

**Installation:**
```bash
uv sync
uv run pytest -q
```
</standard_stack>

<architecture_patterns>
## Architecture Patterns

### Recommended Project Structure
```
src/
|-- llm/               # models registry, client wrapper, retry/fallback policy, budget logic
|-- schemas/           # validation schemas and typed outputs
|-- tools/             # vector manifest + stale check helpers
|-- config.py          # settings loader
scripts/
|-- build_dataset.py   # deterministic 10K sample build and split
`-- seed_vectordb.py   # deterministic embedding/index generation
tests/
|-- test_smoke.py
|-- test_llm_client.py
`-- test_data_pipeline.py
```

### Pattern 1: Centralized Reliability Policy
**What:** Keep retries, fallback chain, timeout, and budget-degrade logic in one client layer.
**When to use:** Multi-model routing with strict consistency requirements.
**Example:**
```python
FALLBACK_CHAIN = [
    "llama-3.3-70b-versatile",
    "mixtral-8x7b-32768",
    "llama-3.1-8b-instant",
]
```

### Pattern 2: Deterministic Artifact Freshness Contract
**What:** Explicit stale decision based on input hash + model id, not clock time.
**When to use:** Expensive preprocessing artifacts that should only rebuild when inputs change.
**Example:**
```python
stale = (manifest.dataset_hash != current_hash) or (manifest.embedding_model != embedding_model_id)
```

### Anti-Patterns to Avoid
- Rebuilding vectors on every startup.
- Duplicating fallback logic across agents.
- Unseeded sampling or implicit split rules.
</architecture_patterns>

<dont_hand_roll>
## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Retry/fallback behavior scattered across modules | ad hoc exception logic per agent | one shared client wrapper | prevents drift and silent inconsistencies |
| Artifact freshness by timestamp only | naive rebuild scheduler | hash-based freshness check | avoids unnecessary rebuilds and startup delays |
| Split contract in multiple scripts | repeated custom split code | single sampling script + metadata manifest | keeps evaluation and demo behavior consistent |

**Key insight:** in this phase, consistency wins over sophistication.
</dont_hand_roll>

<common_pitfalls>
## Common Pitfalls

### Pitfall 1: Reliability policy drift
**What goes wrong:** Different call paths use different trigger/retry/fallback behavior.
**Why it happens:** Policy logic duplicated by convenience.
**How to avoid:** Route all model calls through one client abstraction.
**Warning signs:** Some paths handle 429/timeouts correctly while others fail hard.

### Pitfall 2: Non-reproducible data splits
**What goes wrong:** Teams get different sample distributions, making results unstable.
**Why it happens:** Missing seed lock and split metadata.
**How to avoid:** Fixed seed + explicit split serialization.
**Warning signs:** Holdout metrics vary unexpectedly between machines.

### Pitfall 3: Startup reliability regressions
**What goes wrong:** App startup stalls due repeated heavy reindexing.
**Why it happens:** Missing stale-check contract or improper fallback behavior.
**How to avoid:** Rebuild only on missing/stale, preserve prior valid index on failure.
**Warning signs:** Frequent long startup times without input changes.
</common_pitfalls>

<code_examples>
## Code Examples

### Retry with fallback chain
```python
for model in FALLBACK_CHAIN:
    for attempt in range(max_retries):
        try:
            return call_model(model)
        except RateLimitError:
            backoff_sleep(attempt)
        except (TimeoutError, TransientServerError):
            if attempt == max_retries - 1:
                break
```

### Deterministic split logic
```python
df = filtered_df.sample(frac=1.0, random_state=SEED)
dev, holdout, demos = np.split(df, [7000, 9000])
```

### Stale-check contract
```python
if manifest.dataset_hash != current_hash or manifest.embedding_model != model_id:
    regenerate_index()
```
</code_examples>

<sota_updates>
## State of the Art (2024-2025)

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| pip-only local setup | uv-first setup workflows | faster sync and cleaner reproducibility |
| heuristic fallback handling | explicit fallback policy contracts | fewer runtime surprises |
| unconditional heavy preprocessing | deterministic stale-gated refresh | much better startup behavior |

**New patterns to consider:**
- Manifest-first artifact management.
- Fast-lint + lightweight type checks in early phases.

**Deprecated/outdated:**
- Implicit data contracts and undocumented split logic.
</sota_updates>

## Validation Architecture

Validation for this phase should emphasize fast deterministic feedback:

- Per-task quick checks:
  - `uv run pytest -q tests/test_smoke.py tests/test_llm_client.py`
- Per-wave full checks:
  - `uv run pytest -q && uv run ruff check . && uv run mypy src`

Minimum verification guarantees:
1. Bootstrap path is executable from clean setup.
2. Retry/fallback logic behaves exactly as policy defines.
3. Sampling and stale-check logic are deterministic and regression-tested.

<open_questions>
## Open Questions

1. **CFPB upstream schema drift risk**
   - What we know: current pipeline assumes stable fields for product/issue/narrative.
   - What's unclear: field changes across dataset revisions.
   - Recommendation: add fail-fast schema assertions in sampling script.

2. **Embedding runtime footprint**
   - What we know: `bge-large-en-v1.5` may increase CPU/RAM and seed latency.
   - What's unclear: hardware variance across all demo environments.
   - Recommendation: track seed runtime and surface warning thresholds in logs.
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
- Core technology: bootstrap + reliability + deterministic data/index contracts
- Ecosystem: uv, pytest, ruff, mypy, pandas/pyarrow, chromadb, sentence-transformers
- Patterns: centralized policy modules, manifest/hash freshness checks
- Pitfalls: drift, nondeterminism, startup regressions

**Confidence breakdown:**
- Standard stack: MEDIUM
- Architecture: MEDIUM
- Pitfalls: HIGH
- Code examples: MEDIUM

**Research date:** 2026-04-05
**Valid until:** 2026-05-05
</metadata>

---

*Phase: 01-foundation-and-runtime-baseline*
*Research completed: 2026-04-05 (forced refresh)*
*Ready for planning: yes*