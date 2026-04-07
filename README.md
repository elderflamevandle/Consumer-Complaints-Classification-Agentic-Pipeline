# FinComplaint AI

FinComplaint AI is a local complaint-triage backend for turning a complaint into a compliant, explainable recommended action. The repository currently includes the completed work from Phases 1 through 4:

- deterministic local setup and Groq client reliability scaffolding
- CFPB dataset sampling and vector-index seeding
- PII scrubbing and receipt-text merge for intake
- strict complaint classification and human-review routing
- root-cause retrieval over local complaint history
- MCP-grounded remediation planning
- response writing, compliance audit loop, and explanation output
- SQLite audit logging for node-level decisions

## Current Status

- Complete: Phase 1, Phase 2, Phase 3, Phase 4
- Planned, not implemented yet: Phase 5 Streamlit dashboard, Phase 6 evaluation/fairness, Phase 7 submission hardening
- There is no Streamlit UI entrypoint in the repo yet
- There is no single end-to-end CLI yet; the completed pipeline is exercised through direct scripts, Python APIs, and tests

## Prerequisites

- Python 3.11+
- `uv` for environment and dependency management: https://docs.astral.sh/uv/
- Optional: a `GROQ_API_KEY` if you want live LLM calls instead of only running deterministic tests

## Setup

### PowerShell

```powershell
uv sync
Copy-Item .env.example .env
```

### Bash

```bash
uv sync
cp .env.example .env
```

Update `.env` as needed:

- `GROQ_API_KEY` - required for live Groq-backed agent calls
- `GROQ_BASE_URL` - optional override, defaults to `https://api.groq.com/openai/v1`
- `DAILY_TOKEN_BUDGET` - optional local budget threshold for token tracking

Additional settings supported by `src/config.py` but not required for first run:

- `DATASET_SEED`
- `DATA_DIR`
- `CHROMA_DIR`
- `GROQ_TIMEOUT_SECONDS`
- `GROQ_MAX_RETRIES`
- `GROQ_BACKOFF_BASE_SECONDS`
- `GROQ_BACKOFF_MAX_SECONDS`

## Quick Checks

Sanity-check the local setup:

```powershell
uv run python scripts/tasks.py run
```

Run the optional live Groq smoke test:

```powershell
uv run python scripts/smoke_groq.py
```

Behavior:

- if `GROQ_API_KEY` is set, the script makes one live structured Groq call
- if `GROQ_API_KEY` is missing, it exits cleanly with a skip message

## CFPB Dataset Setup

The repo currently expects a local CFPB CSV export. It does not fetch data from the CFPB API automatically.

Official references:

- CFPB Consumer Complaint Database: https://www.consumerfinance.gov/data-research/consumer-complaints/
- CFPB API docs: https://cfpb.github.io/api/ccdb/api.html
- CFPB field reference: https://cfpb.github.io/api/ccdb/fields.html

### Download the CSV

1. Open the CFPB complaint database page.
2. Download the CSV export from the complaint database page.
3. Extract the archive locally.
4. Note the full path to the extracted CSV file.

### Build the local dataset artifacts

PowerShell example:

```powershell
uv run python scripts/build_dataset.py --input "F:\path\to\complaints.csv"
```

This creates:

- `data/processed/dev.parquet` - 7,000 records
- `data/processed/holdout.parquet` - 2,000 records
- `data/processed/demos.parquet` - 1,000 records
- `data/processed/metadata.json` - seed, counts, and split metadata

Notes:

- the script accepts the official CFPB CSV export headers directly
- `uv sync` installs the required parquet dependencies: `pandas` and `pyarrow`
- if filtering leaves fewer than 10,000 usable narratives, the build fails by design

### Seed the local vector index

```powershell
uv run python scripts/seed_vectordb.py
```

Default behavior:

- reads `data/processed/dev.parquet`
- writes manifest/index artifacts under `chroma_db/`
- seeds up to 5,000 complaint records

The current embedding-model contract is:

```text
bge-large-en-v1.5
```

Fallback behavior:

- if `sentence-transformers` is not installed, the script uses a deterministic hash-based embedding fallback
- if `chromadb` is not installed, the script writes `chroma_db/fallback_index.json`
- Phase 3 retrieval still works against the fallback JSON index through `src/tools/vector_search.py`

If you want the real Chroma + sentence-transformers path, install them and reseed:

```powershell
uv add chromadb sentence-transformers
uv run python scripts/seed_vectordb.py
```

## Commands You Can Run Today

### Cross-platform task runner

These are the stable repo-level commands for the currently completed work:

```powershell
uv run python scripts/tasks.py run
uv run python scripts/tasks.py test
uv run python scripts/tasks.py lint
uv run python scripts/tasks.py typecheck
```

Optional Unix convenience aliases:

```bash
make run
make test
make lint
make typecheck
```

Notes:

- `scripts/tasks.py eval` is a placeholder for the later evaluation phase
- for dataset setup, use `scripts/build_dataset.py` and `scripts/seed_vectordb.py` directly

### Direct scripts

Build dataset:

```powershell
uv run python scripts/build_dataset.py --input "F:\path\to\complaints.csv"
```

Seed vector index:

```powershell
uv run python scripts/seed_vectordb.py
```

Live Groq smoke test:

```powershell
uv run python scripts/smoke_groq.py
```

Inspect the local MCP policy server:

```powershell
uv run python mcp_server/server.py --tool get_sla_requirements --issue-type BILLING --state-code CA
```

Run the full test suite:

```powershell
uv run pytest -q
```

Run lint:

```powershell
uv run ruff check .
```

Run type checks:

```powershell
uv run mypy src
```

Run a narrower test group by phase:

```powershell
uv run pytest -q tests/test_data_pipeline.py
uv run pytest -q tests/test_intake_pipeline.py tests/test_classifier_agent.py tests/test_routing_interrupts.py
uv run pytest -q tests/test_root_cause_agent.py tests/test_remediator_mcp.py tests/test_phase3_graph_logging.py
uv run pytest -q tests/test_response_writer.py tests/test_auditor_loop.py tests/test_explainer_agent.py tests/test_phase4_state.py
```

## Running the Completed Backend Pipeline

There is no packaged end-to-end app command yet. The supported way to exercise the completed pipeline is:

1. build the dataset
2. seed the vector index
3. set `GROQ_API_KEY`
4. run either the tests or a short Python driver script

### Example: run the backend flow from Python

Before running this example:

- `GROQ_API_KEY` must be set for live LLM calls
- `data/processed/dev.parquet` must exist
- `chroma_db/` must already be seeded

PowerShell-ready example:

```powershell
@'
from uuid import uuid4

from src.agents.auditor import AuditorAgent
from src.agents.classifier import ClassifierAgent
from src.agents.explainer import ExplainerAgent
from src.agents.remediator import RemediatorAgent
from src.agents.root_cause import RootCauseAgent
from src.agents.writer import WriterAgent
from src.graph.interrupts import apply_reviewer_action
from src.graph.response_loop import execute_response_loop
from src.graph.routing import build_routing_state
from src.graph.state import ReviewDecision
from src.intake.pipeline import prepare_intake
from src.tools.audit_logger import AuditLogger

complaint_text = (
    "I was charged twice on my credit card, filed a dispute already, "
    "and still have not received a written update."
)
thread_id = f"demo-{uuid4().hex[:8]}"
logger = AuditLogger()

intake = prepare_intake(raw_text=complaint_text, reviewer_available=True)
classification = ClassifierAgent().classify(intake)
state = build_routing_state(
    thread_id=thread_id,
    intake=intake,
    classification=classification,
    audit_logger=logger,
)

if state.review_required:
    state = apply_reviewer_action(
        state,
        ReviewDecision(action="approve", reviewer_notes="Auto-approved for local demo."),
        audit_logger=logger,
    )

diagnosis = RootCauseAgent(audit_logger=logger).diagnose(
    intake.scrubbed_text,
    thread_id=thread_id,
)

remediation = RemediatorAgent(audit_logger=logger).propose_action(
    complaint_text=intake.scrubbed_text,
    classification=state.classification,
    diagnosis=diagnosis,
    state_code="CA",
    thread_id=thread_id,
)

if remediation.status != "ok":
    raise SystemExit(f"Remediation blocked: {remediation.status}")

final_state = execute_response_loop(
    state,
    diagnosis=diagnosis,
    remediation=remediation,
    writer=WriterAgent(audit_logger=logger),
    auditor=AuditorAgent(audit_logger=logger),
)

explanation = ExplainerAgent(audit_logger=logger).summarize_chain(
    classification=final_state.classification,
    diagnosis=diagnosis,
    remediation=remediation,
    final_response=final_state.latest_response_draft,
    audit_verdict=final_state.final_audit,
    thread_id=thread_id,
)

print("thread_id:", thread_id)
print("route:", final_state.route)
print("response_loop_status:", final_state.response_loop_status)
print("resolution_statement:", final_state.latest_response_draft.resolution_statement)
print("audit_verdict:", final_state.final_audit.verdict.value)
print()
print(explanation.render_text())
print()
print("audit_event_count:", len(logger.fetch_events(thread_id=thread_id)))
'@ | uv run python -
```

What this does:

- prepares intake with PII scrubbing
- classifies the complaint
- applies routing and optional human-review continuation
- diagnoses root cause using the seeded local complaint index
- calls the local MCP policy tool before remediation
- runs the writer/auditor loop
- generates the final explanation chain
- writes audit events to `data/audit.db`

## Audit and Local Storage

Generated local artifacts:

- `data/processed/` - sampled parquet datasets and metadata
- `chroma_db/` - vector index manifest and fallback/Chroma index artifacts
- `data/audit.db` - SQLite audit log for node-level decisions

These are local runtime artifacts and should generally not be committed.

## What Is Not Ready Yet

These pieces are planned but not available in the repo today:

- Streamlit dashboard
- UI review controls
- evaluation and fairness harness
- submission-package assets

If you are looking for a UI command such as `streamlit run ...`, that lands in the next phase and is not part of the current codebase.
