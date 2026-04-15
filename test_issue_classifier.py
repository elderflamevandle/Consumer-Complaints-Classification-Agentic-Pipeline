"""
Manual test harness for IssueClassifierAgent.

Run from project root:
    python test_issue_classifier.py

Requires GROQ_API_KEY in .env (loaded automatically).
"""

from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()

from src.agents.issue_classifier import IssueClassifierAgent
from src.agents.prompts import (
    ISSUE_CLASSIFIER_SYSTEM_PROMPT,
    build_issue_classifier_prompt,
)
from src.schemas.classification import ProductType
from src.schemas.taxonomy import format_issue_list_for_prompt, get_display_name

# ---------------------------------------------------------------------------
# Sample inputs — (complaint_text, product, description)
# ---------------------------------------------------------------------------

SAMPLES: list[tuple[str, ProductType, str]] = [
    (
        "I noticed two charges on my credit card I never made — $89 at a store I've "
        "never visited and $210 online. I reported it immediately but the bank refused "
        "to open a dispute and said the charges look legitimate.",
        ProductType.CREDIT_CARD,
        "Credit card fraud / unauthorized charges",
    ),
    (
        "My mortgage servicer applied my payment to fees instead of principal and "
        "interest. They charged me a late fee even though I paid on time. This has "
        "happened three months in a row and they won't fix it.",
        ProductType.MORTGAGE,
        "Mortgage payment misapplication",
    ),
    (
        "A debt collector keeps calling me at work even after I told them to stop. "
        "They called five times yesterday and threatened to have me arrested if I "
        "don't pay immediately.",
        ProductType.DEBT_COLLECTION,
        "FDCPA harassment / illegal threats",
    ),
    (
        "My checking account was charged a $35 overdraft fee even though I had "
        "enough money in my savings account linked for overdraft protection. The bank "
        "refuses to refund the fee.",
        ProductType.CHECKING_SAVINGS_ACCOUNT,
        "Overdraft fee despite linked protection",
    ),
    (
        "The bank closed my account without any notice or explanation. I had $3,400 "
        "in it and they told me a check would be mailed within 30 days. It has been "
        "60 days and I have received nothing.",
        ProductType.CHECKING_SAVINGS_ACCOUNT,
        "Account closure / funds not returned",
    ),
]


def print_separator(title: str = "") -> None:
    line = "=" * 70
    print(f"\n{line}")
    if title:
        print(f"  {title}")
        print(line)


def show_prompt(complaint_text: str, product: ProductType) -> None:
    print("\n--- SYSTEM PROMPT (truncated to 300 chars) ---")
    print(ISSUE_CLASSIFIER_SYSTEM_PROMPT[:300].strip() + "...")
    print("\n--- USER PROMPT ---")
    print(build_issue_classifier_prompt(complaint_text, product))


def show_valid_issues(product: ProductType) -> None:
    display = get_display_name(product.value)
    print(f"\n--- VALID ISSUES FOR: {display} ---")
    print(format_issue_list_for_prompt(product.value))


def run_sample(
    agent: IssueClassifierAgent,
    complaint: str,
    product: ProductType,
    label: str,
    *,
    show_prompts: bool = False,
) -> None:
    print_separator(f"TEST: {label}")
    print(f"Product : {product.value}")
    print(f"Complaint: {complaint[:120]}{'...' if len(complaint) > 120 else ''}")

    if show_prompts:
        show_valid_issues(product)
        show_prompt(complaint, product)

    try:
        result = agent.classify_issue(complaint, product)
        print(f"\nIssue           : {result.issue}")
        print(f"Severity        : {result.severity}")
        print(f"Compliance Risk : {result.compliance_risk}")
        print(f"Confidence      : {result.confidence:.2f}")
        print(f"Reasoning       : {result.reasoning}")
        print(f"LLM attempts    : {agent.last_llm_attempts}")
        print(f"Model           : {agent.last_model}")
        print(f"Tokens used     : {agent.last_total_tokens}")
    except ValueError as e:
        print(f"\nFAILED: {e}")


def main() -> None:
    print_separator("IssueClassifierAgent — Manual Test Harness")
    print("Loading agent...")
    agent = IssueClassifierAgent()

    # Set show_prompts=True on any sample to see the full prompt sent to LLM
    for complaint, product, label in SAMPLES:
        run_sample(agent, complaint, product, label, show_prompts=False)

    print_separator("Done")


if __name__ == "__main__":
    main()
