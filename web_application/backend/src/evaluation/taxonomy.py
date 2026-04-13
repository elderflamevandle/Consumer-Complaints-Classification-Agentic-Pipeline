"""Deterministic normalization from raw CFPB truth labels into classifier enums."""

from __future__ import annotations

import re
from dataclasses import dataclass

from src.schemas.classification import IssueType, ProductType


@dataclass(frozen=True)
class NormalizedTruth:
    raw_product: str
    raw_issue: str
    product_type: ProductType
    issue_type: IssueType


_PRODUCT_MAP: dict[str, ProductType] = {
    'bank account or service': ProductType.BANK_ACCOUNT,
    'checking or savings account': ProductType.BANK_ACCOUNT,
    'consumer loan': ProductType.LOAN,
    'credit card': ProductType.CREDIT_CARD,
    'credit card or prepaid card': ProductType.CREDIT_CARD,
    'credit reporting': ProductType.OTHER,
    'credit reporting or other personal consumer reports': ProductType.OTHER,
    'credit reporting credit repair services or other personal consumer reports': ProductType.OTHER,
    'debt collection': ProductType.DEBT_COLLECTION,
    'debt or credit management': ProductType.OTHER,
    'money transfer virtual currency or money service': ProductType.MONEY_TRANSFER,
    'mortgage': ProductType.MORTGAGE,
    'payday loan title loan or personal loan': ProductType.LOAN,
    'payday loan title loan personal loan or advance loan': ProductType.LOAN,
    'prepaid card': ProductType.CREDIT_CARD,
    'student loan': ProductType.LOAN,
    'vehicle loan or lease': ProductType.LOAN,
}

_CUSTOMER_SERVICE_ISSUES = {
    'account opening closing or management',
    'applying for a mortgage or refinancing an existing mortgage',
    'closing an account',
    'closing cancelling account',
    'closing on a mortgage',
    'closing your account',
    'dealing with my lender or servicer',
    'dealing with your lender or servicer',
    'electronic communications',
    'getting a credit card',
    'managing an account',
    'managing opening or closing account',
    'managing opening or closing your mobile wallet account',
    'managing the loan or lease',
    'opening an account',
    'other features terms or problems',
    'problem with customer service',
    'trouble using the card',
}

_CREDIT_REPORTING_ISSUES = {
    'credit monitoring or identity theft protection services',
    'incorrect information on credit report',
    'incorrect information on your report',
    'improper use of your report',
    'problem with a company s investigation into an existing problem',
    'problem with a credit reporting company s investigation into an existing problem',
    'problem with fraud alerts or security freezes',
    'problem with personal statement of dispute',
    'unable to get your credit report or credit score',
}

_PAYMENT_ISSUES = {
    'loan modification collection foreclosure',
    'loan servicing payments escrow account',
    'money was not available when promised',
    'problem caused by your funds being low',
    'problem when making payments',
    'struggling to pay mortgage',
    'struggling to repay your loan',
    'trouble during payment process',
}

_BILLING_ISSUES = {
    'fees or interest',
    'other transaction problem',
    'problem with a lender or other company charging your account',
    'problem with a purchase or transfer',
    'problem with a purchase shown on your statement',
}

_FRAUD_ISSUES = {
    'fraud or scam',
    'unauthorized transactions or other transaction problem',
}

_OTHER_ISSUES = {
    'attempts to collect debt not owed',
    'communication tactics',
    'cont d attempts collect debt not owed',
    'false statements or representation',
    'took or threatened to take negative or legal action',
    'written notification about debt',
}

_CREDIT_REPORTING_KEYWORDS = (
    'credit report',
    'credit reporting company',
    'credit score',
    'incorrect information on credit report',
    'incorrect information on your report',
    'improper use of my credit report',
    'improper use of your report',
    'investigation',
    'problem with fraud alerts or security freezes',
    'unable to get your credit report or credit score',
    'your report',
)

_BILLING_KEYWORDS = (
    'billing',
    'charged',
    'fees',
    'fee',
    'interest',
    'purchase',
    'statement',
    'unexpected',
    'wrong amount',
)

_PAYMENT_KEYWORDS = (
    'escrow',
    'funds being low',
    'late fee',
    'loan modification',
    'money was not available when promised',
    'pay mortgage',
    'payment',
    'payments',
    'repay your loan',
    'struggling to pay',
    'trouble during payment process',
)

_FRAUD_KEYWORDS = (
    'fraud',
    'scam',
    'unauthorized',
)


def _clean_label(value: str) -> str:
    normalized = re.sub(r'[^a-z0-9]+', ' ', value.strip().lower())
    return re.sub(r'\s+', ' ', normalized).strip()



def normalize_product(product: str) -> ProductType:
    return _PRODUCT_MAP.get(_clean_label(product), ProductType.OTHER)



def normalize_issue(*, product: str, issue: str) -> IssueType:
    product_token = _clean_label(product)
    issue_token = _clean_label(issue)

    if 'identity theft' in issue_token:
        return IssueType.IDENTITY_THEFT

    if issue_token in _CREDIT_REPORTING_ISSUES:
        return IssueType.CREDIT_REPORTING

    if 'credit reporting' in product_token and (
        'monitoring' in issue_token
        or 'fraud alert' in issue_token
        or 'security freez' in issue_token
    ):
        return IssueType.CREDIT_REPORTING

    if any(keyword in issue_token for keyword in _CREDIT_REPORTING_KEYWORDS):
        return IssueType.CREDIT_REPORTING

    if issue_token in _FRAUD_ISSUES:
        return IssueType.FRAUD

    if any(keyword in issue_token for keyword in _FRAUD_KEYWORDS):
        return IssueType.FRAUD

    if issue_token in _PAYMENT_ISSUES:
        return IssueType.PAYMENT

    if issue_token in _BILLING_ISSUES:
        return IssueType.BILLING

    if any(keyword in issue_token for keyword in _BILLING_KEYWORDS):
        return IssueType.BILLING

    if any(keyword in issue_token for keyword in _PAYMENT_KEYWORDS):
        return IssueType.PAYMENT

    if issue_token in _CUSTOMER_SERVICE_ISSUES:
        return IssueType.CUSTOMER_SERVICE

    if issue_token in _OTHER_ISSUES:
        return IssueType.OTHER

    return IssueType.OTHER



def normalize(*, product: str, issue: str) -> NormalizedTruth:
    return NormalizedTruth(
        raw_product=product,
        raw_issue=issue,
        product_type=normalize_product(product),
        issue_type=normalize_issue(product=product, issue=issue),
    )


