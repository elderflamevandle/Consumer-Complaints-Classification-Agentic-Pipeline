from src.evaluation.taxonomy import normalize
from src.schemas.classification import IssueType, ProductType


def test_normalize_maps_supported_product_and_issue_labels() -> None:
    normalized = normalize(
        product='Credit card or prepaid card',
        issue='Problem with a purchase shown on your statement',
    )

    assert normalized.product_type == ProductType.CREDIT_CARD
    assert normalized.issue_type == IssueType.BILLING


def test_normalize_maps_credit_reporting_truth_into_supported_enum_space() -> None:
    normalized = normalize(
        product='Credit reporting, credit repair services, or other personal consumer reports',
        issue="Problem with a credit reporting company's investigation into an existing problem",
    )

    assert normalized.product_type == ProductType.OTHER
    assert normalized.issue_type == IssueType.CREDIT_REPORTING


def test_normalize_is_case_insensitive_for_bank_accounts_and_payment_issues() -> None:
    normalized = normalize(
        product=' Checking or savings account ',
        issue=' Problem when making payments ',
    )

    assert normalized.product_type == ProductType.BANK_ACCOUNT
    assert normalized.issue_type == IssueType.PAYMENT


def test_normalize_preserves_identity_theft_signal_from_raw_issue_text() -> None:
    normalized = normalize(
        product='Credit reporting or other personal consumer reports',
        issue='Identity theft protection or other monitoring services',
    )

    assert normalized.product_type == ProductType.OTHER
    assert normalized.issue_type == IssueType.IDENTITY_THEFT


def test_normalize_uses_other_for_unsupported_or_ambiguous_labels() -> None:
    normalized = normalize(
        product='Debt or credit management',
        issue='Other service problem',
    )

    assert normalized.product_type == ProductType.OTHER
    assert normalized.issue_type == IssueType.OTHER
