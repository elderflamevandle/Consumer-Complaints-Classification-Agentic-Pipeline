"""Official CFPB product → issue taxonomy.

This is the single source of truth for the two-stage classification pipeline.
Both ProductClassifierAgent and IssueClassifierAgent read from here.

Key design decisions:
- Product keys are UPPER_SNAKE_CASE enum codes (used in ClassificationResult).
- Issue values are the EXACT CFPB display strings (used verbatim in prompts and
  stored in IssueType StrEnum so that `.value` returns the display label).
- Many issues appear across multiple products — they are shared by reference,
  not duplicated, ensuring the taxonomy stays consistent.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Shared issue strings (used by multiple products)
# ---------------------------------------------------------------------------

_CREDIT_MONITORING = "Credit monitoring or identity theft protection services"
_IMPROPER_USE_OF_REPORT = "Improper use of your report"
_INCORRECT_INFORMATION = "Incorrect information on your report"
_INVESTIGATION_EXISTING_PROBLEM = "Problem with a company's investigation into an existing problem"
_FRAUD_ALERTS = "Problem with fraud alerts or security freezes"
_UNABLE_CREDIT_REPORT = "Unable to get your credit report or credit score"

# ---------------------------------------------------------------------------
# Official CFPB product → issue hierarchy
# Keys are ProductType enum values; list entries are exact CFPB issue labels.
# ---------------------------------------------------------------------------

PRODUCT_ISSUE_HIERARCHY: dict[str, list[str]] = {
    "CHECKING_SAVINGS_ACCOUNT": [
        "Closing an account",
        _CREDIT_MONITORING,
        _IMPROPER_USE_OF_REPORT,
        _INCORRECT_INFORMATION,
        "Managing an account",
        "Opening an account",
        "Problem caused by your funds being low",
        _INVESTIGATION_EXISTING_PROBLEM,
        "Problem with a lender or other company charging your account",
        _FRAUD_ALERTS,
        _UNABLE_CREDIT_REPORT,
    ],
    "CREDIT_CARD": [
        "Advertising and marketing, including promotional offers",
        "Closing your account",
        _CREDIT_MONITORING,
        "Fees or interest",
        "Getting a credit card",
        _IMPROPER_USE_OF_REPORT,
        _INCORRECT_INFORMATION,
        "Other features, terms, or problems",
        "Problem when making payments",
        _INVESTIGATION_EXISTING_PROBLEM,
        "Problem with a purchase shown on your statement",
        _FRAUD_ALERTS,
        "Struggling to pay your bill",
        "Trouble using your card",
        _UNABLE_CREDIT_REPORT,
    ],
    "CREDIT_REPORTING": [
        _CREDIT_MONITORING,
        "Identity theft protection or other monitoring services",
        _IMPROPER_USE_OF_REPORT,
        _INCORRECT_INFORMATION,
        "Problem with a company's investigation into an existing issue",
        _INVESTIGATION_EXISTING_PROBLEM,
        _FRAUD_ALERTS,
        _UNABLE_CREDIT_REPORT,
    ],
    "DEBT_COLLECTION": [
        "Attempts to collect debt not owed",
        "Communication tactics",
        "Electronic communications",
        "False statements or representation",
        "Threatened to contact someone or share information improperly",
        "Took or threatened to take negative or legal action",
        "Written notification about debt",
    ],
    "MONEY_TRANSFER": [
        "Confusing or misleading advertising or marketing",
        "Confusing or missing disclosures",
        "Fraud or scam",
        "Incorrect exchange rate",
        "Lost or stolen money order",
        "Managing, opening, or closing your mobile wallet account",
        "Money was not available when promised",
        "Other service problem",
        "Other transaction problem",
        "Overdraft, savings, or rewards features",
        "Problem adding money",
        "Problem with customer service",
        "Trouble accessing funds in your mobile or digital wallet",
        "Unauthorized transactions or other transaction problem",
        "Unexpected or other fees",
        "Wrong amount charged or received",
    ],
    "MORTGAGE": [
        "Applying for a mortgage or refinancing an existing mortgage",
        "Closing on a mortgage",
        _IMPROPER_USE_OF_REPORT,
        _INCORRECT_INFORMATION,
        _INVESTIGATION_EXISTING_PROBLEM,
        "Struggling to pay mortgage",
        "Trouble during payment process",
        _UNABLE_CREDIT_REPORT,
    ],
    "VEHICLE_LOAN_LEASE": [
        "Getting a loan or lease",
        _IMPROPER_USE_OF_REPORT,
        _INCORRECT_INFORMATION,
        "Managing the loan or lease",
        _INVESTIGATION_EXISTING_PROBLEM,
        "Problems at the end of the loan or lease",
        "Repossession",
        "Struggling to pay your loan",
    ],
}

# ---------------------------------------------------------------------------
# Product display labels (human-readable names for UI / prompts)
# ---------------------------------------------------------------------------

PRODUCT_DISPLAY_NAMES: dict[str, str] = {
    "CHECKING_SAVINGS_ACCOUNT": "Checking or savings account",
    "CREDIT_CARD": "Credit card",
    "CREDIT_REPORTING": "Credit reporting or other personal consumer reports",
    "DEBT_COLLECTION": "Debt collection",
    "MONEY_TRANSFER": "Money transfer, virtual currency, or money service",
    "MORTGAGE": "Mortgage",
    "VEHICLE_LOAN_LEASE": "Vehicle loan or lease",
}

# ---------------------------------------------------------------------------
# Derived helpers
# ---------------------------------------------------------------------------

ALL_PRODUCTS: list[str] = list(PRODUCT_ISSUE_HIERARCHY.keys())

# All unique issue strings across all products (sorted for stable ordering)
ALL_ISSUES: list[str] = sorted(
    {issue for issues in PRODUCT_ISSUE_HIERARCHY.values() for issue in issues}
)


def get_issues_for_product(product_key: str) -> list[str]:
    """Return the ordered list of valid CFPB issue strings for a product key.

    Falls back to the full ALL_ISSUES list if the key is unrecognised.
    """
    return PRODUCT_ISSUE_HIERARCHY.get(product_key.strip().upper(), ALL_ISSUES)


def get_display_name(product_key: str) -> str:
    """Return the human-readable CFPB product name for a product key."""
    return PRODUCT_DISPLAY_NAMES.get(product_key.strip().upper(), product_key)


def format_issue_list_for_prompt(product_key: str) -> str:
    """Return a numbered issue list for injection into a classifier prompt."""
    issues = get_issues_for_product(product_key)
    return "\n".join(f'  {i + 1}. "{issue}"' for i, issue in enumerate(issues))


def format_product_list_for_prompt() -> str:
    """Return a numbered product list (with display names) for prompts."""
    lines = []
    for i, (key, label) in enumerate(PRODUCT_DISPLAY_NAMES.items(), start=1):
        lines.append(f'  {i}. "{key}" — {label}')
    return "\n".join(lines)
