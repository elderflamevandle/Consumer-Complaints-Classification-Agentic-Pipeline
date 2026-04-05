# Stack Research

**Domain:** Agentic AI complaint resolution platform for consumer finance operations
**Researched:** 2026-04-05
**Confidence:** MEDIUM

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.11+ | Main runtime | Strong ecosystem for LangGraph, data tooling, and rapid prototype iteration |
| LangGraph | >=0.4 | Agent workflow orchestration | Native graph routing, conditional edges, interrupts, and cyclic flows for HITL/auditor loops |
| OpenAI SDK (Groq-compatible base URL) | >=1.50 | LLM client transport | Clean API surface for JSON outputs, retries, and model-routing abstraction |
| Pydantic | >=2.7 | Structured schema validation | Enforces parseable outputs and prevents silent prompt-format drift |
| Streamlit | >=1.38 | Demo UI layer | Fastest path to an inspectable interactive dashboard with low front-end overhead |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| chromadb | >=0.5 | Local vector retrieval | Root-cause agent retrieval over prior complaint narratives |
| sentence-transformers | >=3.0 | Embeddings (`all-MiniLM-L6-v2`) | Offline embedding generation for 5K sample corpus |
| presidio-analyzer + presidio-anonymizer | >=2.2 | PII detection/anonymization | Always run before LLM calls to reduce leakage risk |
| spacy | >=3.7 | NLP model dependency for Presidio | Use `en_core_web_sm` for lower compute footprint |
| fastapi | >=0.110 | Optional API wrapper | Needed if exposing pipeline beyond Streamlit in v1.x |
| scikit-learn | >=1.5 | Evaluation metrics | Macro F1, confusion matrix, and fairness metric support |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| pytest | Unit and integration tests | Prioritize fallback routing and graph edge-case tests |
| Makefile | Repeatable dev tasks | Add `make seed-db`, `make run`, `make eval` shortcuts |
| SQLite | Local audit store | Zero-cost durable decision logging for demos |

## Installation

```bash
# Core
pip install langgraph langchain-core openai pydantic pydantic-settings streamlit

# Supporting
pip install chromadb sentence-transformers presidio-analyzer presidio-anonymizer spacy scikit-learn
python -m spacy download en_core_web_sm

# Optional API wrapper
pip install fastapi uvicorn
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| LangGraph | Custom orchestrator | Only if graph logic is trivial and no interrupt/cycle behavior is needed |
| ChromaDB local | Managed vector DB | If multi-user concurrent retrieval or hosted persistence is required |
| Streamlit | React + FastAPI custom UI | If production-grade UX is a core requirement, not demo velocity |
| OpenAI SDK with Groq base URL | Native Groq SDK | If team prefers native SDK ergonomics and no OpenAI API compatibility layer |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Non-existent Groq fallback model names | Breaks fallback logic at runtime | `mixtral-8x7b-32768` then `llama-3.1-8b-instant` |
| Running embedding creation in request thread | Causes latency spikes and app freezes | Offline batch script (`scripts/seed_vectordb.py`) |
| Skipping schema validation for LLM outputs | Hidden parse failures and brittle downstream logic | Pydantic models + retry on invalid JSON |
| Premature microservice decomposition | Adds orchestration overhead in one-week sprint | Single-repo modular architecture |

## Stack Patterns by Variant

**If demo reliability is top priority:**
- Keep all persistence local (SQLite + local Chroma)
- Use deterministic temperature settings (`0.0` or `0.1`)

**If evaluation depth becomes priority:**
- Add offline batch evaluator pipeline
- Keep LLM judge optional to protect rate limits

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| langgraph>=0.4 | langchain-core>=0.3 | Keep aligned for graph and checkpoint APIs |
| presidio-analyzer>=2.2 | spacy>=3.7 | Use small model to avoid unnecessary CPU load |
| chromadb>=0.5 | sentence-transformers>=3.0 | Stable local embedding/retrieval workflow |

## Sources

- `f:/Agentic_Hackathon/plan2.md` - primary architecture and execution intent
- `f:/Agentic_Hackathon/plan.md` - supporting fallback and evaluation patterns
- Internal project constraints from `.planning/PROJECT.md`

---
*Stack research for: Agentic AI complaint resolution platform for consumer finance operations*
*Researched: 2026-04-05*
