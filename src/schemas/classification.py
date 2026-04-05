"""Classification schema contracts used by classifier output parsing."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProductType(StrEnum):
    CREDIT_CARD = 'CREDIT_CARD'
    BANK_ACCOUNT = 'BANK_ACCOUNT'
    MORTGAGE = 'MORTGAGE'
    LOAN = 'LOAN'
    DEBT_COLLECTION = 'DEBT_COLLECTION'
    MONEY_TRANSFER = 'MONEY_TRANSFER'
    OTHER = 'OTHER'


class IssueType(StrEnum):
    BILLING = 'BILLING'
    FRAUD = 'FRAUD'
    PAYMENT = 'PAYMENT'
    IDENTITY_THEFT = 'IDENTITY_THEFT'
    CUSTOMER_SERVICE = 'CUSTOMER_SERVICE'
    CREDIT_REPORTING = 'CREDIT_REPORTING'
    OTHER = 'OTHER'


class SeverityLevel(StrEnum):
    LOW = 'LOW'
    MEDIUM = 'MEDIUM'
    HIGH = 'HIGH'
    CRITICAL = 'CRITICAL'


class ComplianceRisk(StrEnum):
    LOW = 'LOW'
    MEDIUM = 'MEDIUM'
    HIGH = 'HIGH'


_NORMALIZED_ALIASES: dict[str, str] = {
    'CREDITCARD': 'CREDIT_CARD',
    'BANKACCOUNT': 'BANK_ACCOUNT',
    'DEBTCOLLECTION': 'DEBT_COLLECTION',
    'MONEYTRANSFER': 'MONEY_TRANSFER',
    'IDENTITYTHEFT': 'IDENTITY_THEFT',
    'CUSTOMERSERVICE': 'CUSTOMER_SERVICE',
    'CREDITREPORTING': 'CREDIT_REPORTING',
}


def _normalize_enum_token(value: str) -> str:
    token = value.strip().upper().replace('-', '_').replace(' ', '_')
    squash = token.replace('_', '')
    if squash in _NORMALIZED_ALIASES:
        return _NORMALIZED_ALIASES[squash]
    return token


class ClassificationResult(BaseModel):
    model_config = ConfigDict(extra='forbid')

    product_type: ProductType
    issue_type: IssueType
    severity: SeverityLevel
    compliance_risk: ComplianceRisk
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator('product_type', 'issue_type', 'severity', 'compliance_risk', mode='before')
    @classmethod
    def _normalize_enum_input(cls, value: object) -> object:
        if isinstance(value, str):
            return _normalize_enum_token(value)
        return value