import os
import sys
from openai import OpenAI
from dotenv import load_dotenv

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
        sys.stderr.reconfigure(encoding="utf-8", line_buffering=True)
    except Exception:
        pass

load_dotenv()

# ---------------------------------------------------------------------------
# Test cases — (issue, state, category)
# Covers credit, lending, collections, fraud, and servicing complaint types
# ---------------------------------------------------------------------------
TEST_CASES = [
    # Credit card
    ("Unauthorized charge on credit card — cardholder disputes transaction",   "California",    "Credit Card / Reg Z"),
    ("Credit card billing error — finance charge applied after full payment",   "Texas",         "Credit Card / Reg Z"),

    # Mortgage
    ("Mortgage servicer misapplied monthly payment to wrong account",          "Florida",       "Mortgage / RESPA"),
    ("Foreclosure initiated while loss-mitigation application was pending",     "New York",      "Mortgage / CFPB Rule"),

    # Student loans
    ("Federal student loan servicer failed to apply income-driven repayment",  "Illinois",      "Student Loan / FSA"),
    ("Private student loan servicer refused to provide payoff statement",       "Ohio",          "Student Loan / TILA"),

    # Auto loans
    ("Auto lender applied extra fees after loan payoff — balance dispute",      "Georgia",       "Auto Loan / TILA"),

    # Debt collection
    ("Debt collector called outside permitted hours — FDCPA violation claim",   "Washington",    "Debt Collection / FDCPA"),
    ("Debt collector threatened legal action on time-barred debt",              "Massachusetts", "Debt Collection / FDCPA"),

    # Bank accounts / wire transfers
    ("Unauthorized electronic fund transfer — bank refused to investigate",     "Nevada",        "EFT / Reg E"),
    ("Wire transfer sent to wrong account — bank refused reversal request",     "Virginia",      "Wire / UCC Article 4A"),

    # Credit reporting
    ("Incorrect derogatory mark on credit report — dispute ignored by bureau",  "Colorado",      "Credit Reporting / FCRA"),

    # Payday / small-dollar lending
    ("Payday lender rolled over loan without consent — excessive fees charged", "Michigan",      "Payday / State Law"),

    # Prepaid cards
    ("Prepaid card issuer blocked access to funds without notice or reason",    "Arizona",       "Prepaid / Reg E"),
]

SYSTEM_PROMPT = """You are a Senior Fintech Compliance Officer with expertise in U.S. federal and state consumer financial regulations (CFPB, FDCPA, FCRA, RESPA, TILA, Regulation E, Regulation Z, UCC Article 4A).

Your sole function is to output structured SLA compliance data. You do not greet, explain, or pad responses. Every field must be populated — never leave a field blank."""

def build_prompt(issue: str, state: str) -> str:
    return f"""COMPLAINT DETAILS
Issue       : {issue}
Jurisdiction: {state}, USA

OUTPUT FORMAT — use exactly these labels, one per line, no extra text:

DEADLINE    : <number> days  |  OR  |  Escalate to Legal
REGULATION  : <specific law / rule name and section, e.g., "Regulation Z, 12 CFR 1026.13(c)">
AUTHORITY   : <enforcing body, e.g., "CFPB", "FTC", "State AG">
PENALTY     : <consequence for non-compliance, e.g., "Actual damages + $1,000 statutory + attorney fees">
ESCALATION  : <next step if deadline is missed, e.g., "File CFPB complaint; potential UDAAP enforcement">
NOTES       : <one sentence — state-specific override if applicable, else "Federal baseline applied">

STRICT RULES
1. Cite the exact CFR section or statute where known (e.g., 15 U.S.C. § 1692c).
2. If state law imposes a SHORTER deadline than federal, use the state deadline and note it.
3. Never invent numbers. If the deadline is genuinely unknown, write: DEADLINE: Escalate to Legal
4. No prose, no pleasantries, no markdown — plain labelled lines only."""


def run_inference():
    hf_token = os.environ.get("HF_TOKEN")
    if not hf_token:
        print("ERROR: HF_TOKEN is not set.")
        print("  Windows:   set HF_TOKEN=hf_your_token_here")
        print("  Mac/Linux: export HF_TOKEN=hf_your_token_here")
        sys.exit(1)

    client = OpenAI(
        base_url="https://router.huggingface.co/v1",
        api_key=hf_token,
    )

    model_name = "google/gemma-4-31B-it"

    print(f"Model : {model_name}", flush=True)
    print(f"Cases : {len(TEST_CASES)}", flush=True)
    print("=" * 70, flush=True)

    passed, failed = 0, 0

    for idx, (issue, state, category) in enumerate(TEST_CASES, start=1):
        header = f"[{idx:02d}/{len(TEST_CASES)}] {category} — {state}"
        print(f"\n{header}", flush=True)
        print(f"  Issue : {issue}", flush=True)
        print("-" * 70, flush=True)

        try:
            completion = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": build_prompt(issue, state)},
                ],
                max_tokens=1000,
                temperature=0.1,
            )
            response_text = completion.choices[0].message.content.strip()
            print("RESPONSE:", flush=True)
            print(response_text, flush=True)
            passed += 1

        except Exception as exc:
            print(f"  FAILED: {exc}", flush=True)
            failed += 1

        print(flush=True)

    # Summary
    print("=" * 70, flush=True)
    print(f"DONE  — {passed} passed, {failed} failed out of {len(TEST_CASES)} cases.", flush=True)
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    run_inference()
