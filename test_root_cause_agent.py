"""
End-to-end manual test harness for RootCauseAgent.

Tests the full chain:
  1. ChromaDB vector search  ->  retrieve similar historical complaints
  2. Groq LLM               ->  diagnose root cause from evidence
  3. MCP policy server       ->  fetch SLA + compliance laws for the issue

Run from project root:
    python test_root_cause_agent.py

Requires GROQ_API_KEY in .env (loaded automatically).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Force mock fallback so the bridge never hits live APIs (avoids subprocess hang)
os.environ.setdefault("LEGAL_MCP_USE_MOCK_FALLBACK", "1")

# --- core pipeline imports ---
from src.agents.root_cause import RootCauseAgent
from src.agents.prompts import build_root_cause_prompt
from src.schemas.root_cause import RootCauseResult
from src.tools.vector_search import RetrievedCase, retrieve_similar_cases

# Call the bridge directly — bypasses the subprocess that hangs on live API calls
from legal_knowledge_mcp.bridge import get_sla_requirements

# ---------------------------------------------------------------------------
# Sample complaints to test — (label, complaint_text, issue_type, state_code)
# issue_type + state_code are passed to the MCP server for compliance lookup.
# ---------------------------------------------------------------------------

SAMPLES: list[tuple[str, str, str, str]] = [
    (
        "Credit card fraud / unauthorized charges",
        (
            "I noticed two charges on my credit card I never made — $89 at a store "
            "I've never visited and $210 online. I reported it to my bank immediately "
            "but they refused to open a dispute, saying the charges look legitimate. "
            "I have never shared my card details with anyone."
        ),
        "Fraud or scam",
        "CA",
    ),
    (
        "Mortgage servicer payment misapplication",
        (
            "My mortgage servicer has applied my last three payments to fees and "
            "escrow instead of principal and interest. They also charged me a $45 "
            "late fee even though I paid on time. I've called five times and no one "
            "can explain the payment history. They threatened foreclosure."
        ),
        "Struggling to pay mortgage",
        "TX",
    ),
    (
        "Debt collector harassment / FDCPA violation",
        (
            "A debt collection agency keeps calling me at my workplace even after I "
            "sent a written cease-and-desist letter. They call 6–8 times per day, "
            "threatened to have me arrested, and contacted my employer directly "
            "disclosing the debt amount. This has been going on for three weeks."
        ),
        "Communication tactics",
        "NY",
    ),
    (
        "Checking account wrongful closure / funds withheld",
        (
            "My bank closed my checking account without any warning or explanation. "
            "I had $3,400 inside. They said a check would arrive within 30 business "
            "days — it has now been 70 days and I have received nothing. Customer "
            "service refuses to escalate. I need those funds to pay rent."
        ),
        "Closing an account",
        "FL",
    ),
    (
        "Credit reporting — inaccurate derogatory mark",
        (
            "A collection account for a debt I already paid in full two years ago is "
            "still showing as 'unpaid' on my credit report. I disputed it with all "
            "three bureaus and submitted proof of payment. 45 days later the bureaus "
            "say the original creditor 'verified' it — but the debt is clearly settled."
        ),
        "Incorrect information on your report",
        "IL",
    ),
]


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def sep(title: str = "") -> None:
    print("\n" + "=" * 72)
    if title:
        print(f"  {title}")
        print("=" * 72)


def print_retrieved_cases(cases: list[RetrievedCase]) -> None:
    if not cases:
        print("  [no cases retrieved — ChromaDB may be empty]")
        return
    for c in cases:
        print(
            f"  [{c.score:.4f}] id={c.id}  product={c.product}\n"
            f"           issue={c.issue}  date={c.date}  state={c.state or 'N/A'}\n"
            f"           narrative={c.narrative[:140]}..."
        )


def print_root_cause(result: RootCauseResult) -> None:
    print(f"\n  Root Cause     : {result.root_cause}")
    print(f"  Ambiguity Flag : {result.ambiguity_flag}")
    print(f"  Evidence ({len(result.evidence)} items):")
    for ev in result.evidence:
        print(
            f"    #{ev.rank} [score={ev.score:.4f}] {ev.summary[:100]}\n"
            f"         cite -> {ev.citation.product} / {ev.citation.issue} / {ev.citation.date}"
        )


def print_policy(policy: dict) -> None:
    print(f"\n  MCP Policy Lookup (source: {policy.get('source', 'unknown')}):")
    print(f"    Issue Type       : {policy.get('issue_type', 'N/A')}")
    print(f"    State            : {policy.get('state_code', 'N/A')}")
    print(f"    SLA Window       : {policy.get('sla_window', 'N/A')}")
    print(f"    Regulatory Basis : {policy.get('regulatory_basis', 'N/A')}")
    print(f"    Required Actions :")
    for action in policy.get("required_actions", []):
        print(f"      - {action}")
    citations = policy.get("legal_citations", [])
    if citations:
        print(f"    Legal Citations  :")
        for cite in citations[:3]:
            print(f"      *{cite.get('title', 'N/A')} — {cite.get('url', '')}")


def print_prompt_preview(complaint_text: str, cases: list[RetrievedCase]) -> None:
    prompt = build_root_cause_prompt(complaint_text, cases)
    print("\n  --- PROMPT SENT TO LLM (first 600 chars) ---")
    print(prompt[:600].strip() + "\n  ...")


# ---------------------------------------------------------------------------
# Single test runner
# ---------------------------------------------------------------------------

def run_sample(
    label: str,
    complaint_text: str,
    issue_type: str,
    state_code: str,
    *,
    agent: RootCauseAgent,
    show_prompt: bool = False,
    retrieval_limit: int = 5,
) -> None:
    sep(f"TEST: {label}")
    print(f"  Complaint  : {complaint_text[:130]}...")
    print(f"  Issue Type : {issue_type}  |  State: {state_code}")

    # ── Step 1: Vector retrieval ──────────────────────────────────────────
    print("\n  [1] ChromaDB vector retrieval...")
    cases = retrieve_similar_cases(query_text=complaint_text, limit=retrieval_limit)
    print(f"  Retrieved {len(cases)} case(s):")
    print_retrieved_cases(cases)

    if show_prompt:
        print_prompt_preview(complaint_text, cases)

    # ── Step 2: LLM root-cause diagnosis ─────────────────────────────────
    print("\n  [2] LLM root-cause diagnosis...")
    try:
        result = agent.diagnose(complaint_text)
        print_root_cause(result)
        print(f"\n  LLM attempts : {agent.last_llm_attempts}")
        print(f"  Model        : {agent.last_model}")
        print(f"  Tokens used  : {agent.last_total_tokens}")
        print(f"  Used fallback: {agent.used_fallback}")
    except Exception as exc:
        print(f"  DIAGNOSIS FAILED: {exc}")

    # ── Step 3: MCP compliance / SLA lookup (direct bridge, no subprocess) ──
    print(f"\n  [3] MCP policy lookup — issue='{issue_type}', state='{state_code}'...")
    try:
        policy = get_sla_requirements(issue_type=issue_type, state_code=state_code)
        print_policy(policy)
    except Exception as exc:
        print(f"  POLICY LOOKUP FAILED: {exc}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    sep("RootCauseAgent — End-to-End Test Harness")
    print("  Chain: ChromaDB retrieval -> Groq LLM diagnosis -> MCP SLA/compliance lookup")

    agent = RootCauseAgent()

    # Set show_prompt=True on any call to see the full LLM prompt
    for label, complaint, issue_type, state_code in SAMPLES:
        run_sample(
            label,
            complaint,
            issue_type,
            state_code,
            agent=agent,
            show_prompt=False,
            retrieval_limit=5,
        )

    sep("Done")


if __name__ == "__main__":
    main()
