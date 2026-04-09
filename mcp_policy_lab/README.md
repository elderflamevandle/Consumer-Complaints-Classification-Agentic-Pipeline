# MCP Policy Lab (Isolated from Main Pipeline)

This folder is a standalone implementation sandbox for policy/law retrieval.
It is **not** wired into `src/` or the current complaint pipeline.

## Goal

Provide a practical multi-source policy resolver with this precedence:

1. Dummy local rules (deterministic, offline)
2. GovInfo MCP endpoint (federal source)
3. Open Legal Codes API/MCP-backed service (state/local code text)
4. Serper web-search fallback (discovery only)

## Why this is separate

You asked to avoid implementing in the existing code path. Everything here runs independently.

## Quick start

1. Copy `.env.example` to `.env` and fill keys as needed.
2. Run:

```powershell
python mcp_policy_lab\demo.py --issue "Fraud or scam" --state NY
```

## Regenerate full dummy norms

This generates all 50 state entries plus all CFPB issue keys (currently 54):

```powershell
python -m mcp_policy_lab.generate_dummy_policy_rules
```

## Notes on free access and keys

- `dummy`: free, local file
- `govinfo_mcp`: requires API key header from api.data.gov (key signup is free)
- `open_legal_codes`: currently no signup/key required (per provider docs)
- `serper`: requires key; free starter credits exist, then paid top-ups

## Files

- `dummy_policy_rules.json`: dummy regulations data
- `providers/`: source connectors
- `resolver.py`: orchestration and precedence logic
- `demo.py`: CLI demo
