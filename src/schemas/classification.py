"""Classification schema contracts for the two-stage complaint classifier.

Design:
  - ProductType: UPPER_SNAKE_CASE StrEnum codes (7 CFPB product categories).
  - IssueType:   StrEnum where the VALUE is the exact CFPB display string.
                 This means `.value` always returns the human-readable label,
                 making all downstream `.issue_type.value` calls correct without
                 any code changes.
  - SeverityLevel / ComplianceRisk: unchanged.
  - ClassificationResult: backward-compatible merged output from both stages.
  - ProductClassificationResult: Stage-1 output (product only).
  - IssueClassificationResult:   Stage-2 output (issue + severity + risk).
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# Product taxonomy codes (7 CFPB categories)
# ---------------------------------------------------------------------------

class ProductType(StrEnum):
    CHECKING_SAVINGS_ACCOUNT = 'CHECKING_SAVINGS_ACCOUNT'
    CREDIT_CARD = 'CREDIT_CARD'
    CREDIT_REPORTING = 'CREDIT_REPORTING'
    DEBT_COLLECTION = 'DEBT_COLLECTION'
    MONEY_TRANSFER = 'MONEY_TRANSFER'
    MORTGAGE = 'MORTGAGE'
    VEHICLE_LOAN_LEASE = 'VEHICLE_LOAN_LEASE'


# ---------------------------------------------------------------------------
# Issue taxonomy — StrEnum where value = exact CFPB display string
# Calling `.value` returns the human-readable label (e.g. "Closing an account")
# ---------------------------------------------------------------------------

class IssueType(StrEnum):
    # --- Shared across multiple products ---
    CREDIT_MONITORING = "Credit monitoring or identity theft protection services"
    IMPROPER_USE_OF_REPORT = "Improper use of your report"
    INCORRECT_INFORMATION = "Incorrect information on your report"
    INVESTIGATION_EXISTING_PROBLEM = "Problem with a company's investigation into an existing problem"
    FRAUD_ALERTS = "Problem with fraud alerts or security freezes"
    UNABLE_CREDIT_REPORT = "Unable to get your credit report or credit score"

    # --- Checking / Savings Account ---
    CLOSING_AN_ACCOUNT = "Closing an account"
    MANAGING_AN_ACCOUNT = "Managing an account"
    OPENING_AN_ACCOUNT = "Opening an account"
    FUNDS_LOW = "Problem caused by your funds being low"
    LENDER_CHARGING_ACCOUNT = "Problem with a lender or other company charging your account"

    # --- Credit Card ---
    ADVERTISING_AND_MARKETING = "Advertising and marketing, including promotional offers"
    CLOSING_YOUR_ACCOUNT = "Closing your account"
    FEES_OR_INTEREST = "Fees or interest"
    GETTING_A_CREDIT_CARD = "Getting a credit card"
    OTHER_FEATURES_TERMS = "Other features, terms, or problems"
    PROBLEM_WHEN_MAKING_PAYMENTS = "Problem when making payments"
    PURCHASE_ON_STATEMENT = "Problem with a purchase shown on your statement"
    STRUGGLING_TO_PAY_BILL = "Struggling to pay your bill"
    TROUBLE_USING_CARD = "Trouble using your card"

    # --- Credit Reporting ---
    IDENTITY_THEFT_PROTECTION = "Identity theft protection or other monitoring services"
    INVESTIGATION_EXISTING_ISSUE = "Problem with a company's investigation into an existing issue"

    # --- Debt Collection ---
    ATTEMPTS_TO_COLLECT_NOT_OWED = "Attempts to collect debt not owed"
    COMMUNICATION_TACTICS = "Communication tactics"
    ELECTRONIC_COMMUNICATIONS = "Electronic communications"
    FALSE_STATEMENTS = "False statements or representation"
    THREATENED_SHARE_INFO = "Threatened to contact someone or share information improperly"
    NEGATIVE_OR_LEGAL_ACTION = "Took or threatened to take negative or legal action"
    WRITTEN_NOTIFICATION = "Written notification about debt"

    # --- Money Transfer ---
    CONFUSING_ADVERTISING = "Confusing or misleading advertising or marketing"
    CONFUSING_DISCLOSURES = "Confusing or missing disclosures"
    FRAUD_OR_SCAM = "Fraud or scam"
    INCORRECT_EXCHANGE_RATE = "Incorrect exchange rate"
    LOST_STOLEN_MONEY_ORDER = "Lost or stolen money order"
    MOBILE_WALLET_MANAGEMENT = "Managing, opening, or closing your mobile wallet account"
    MONEY_NOT_AVAILABLE = "Money was not available when promised"
    OTHER_SERVICE_PROBLEM = "Other service problem"
    OTHER_TRANSACTION_PROBLEM = "Other transaction problem"
    OVERDRAFT_SAVINGS_REWARDS = "Overdraft, savings, or rewards features"
    PROBLEM_ADDING_MONEY = "Problem adding money"
    CUSTOMER_SERVICE = "Problem with customer service"
    TROUBLE_ACCESSING_WALLET = "Trouble accessing funds in your mobile or digital wallet"
    UNAUTHORIZED_TRANSACTIONS = "Unauthorized transactions or other transaction problem"
    UNEXPECTED_FEES = "Unexpected or other fees"
    WRONG_AMOUNT = "Wrong amount charged or received"

    # --- Mortgage ---
    APPLYING_FOR_MORTGAGE = "Applying for a mortgage or refinancing an existing mortgage"
    CLOSING_ON_MORTGAGE = "Closing on a mortgage"
    STRUGGLING_TO_PAY_MORTGAGE = "Struggling to pay mortgage"
    TROUBLE_DURING_PAYMENT = "Trouble during payment process"

    # --- Vehicle Loan / Lease ---
    GETTING_LOAN_OR_LEASE = "Getting a loan or lease"
    MANAGING_LOAN_OR_LEASE = "Managing the loan or lease"
    PROBLEMS_END_OF_LOAN = "Problems at the end of the loan or lease"
    REPOSSESSION = "Repossession"
    STRUGGLING_TO_PAY_LOAN = "Struggling to pay your loan"


# ---------------------------------------------------------------------------
# Severity and compliance risk
# ---------------------------------------------------------------------------

class SeverityLevel(StrEnum):
    LOW = 'LOW'
    MEDIUM = 'MEDIUM'
    HIGH = 'HIGH'
    CRITICAL = 'CRITICAL'


class ComplianceRisk(StrEnum):
    LOW = 'LOW'
    MEDIUM = 'MEDIUM'
    HIGH = 'HIGH'


# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------

def _normalize_product_token(value: str) -> str:
    """Normalise a product string to a ProductType enum key."""
    token = value.strip().upper().replace('-', '_').replace(' ', '_')
    # Handle legacy codes from old taxonomy
    aliases = {
        'BANK_ACCOUNT': 'CHECKING_SAVINGS_ACCOUNT',
        'BANKACCOUNT': 'CHECKING_SAVINGS_ACCOUNT',
        'LOAN': 'VEHICLE_LOAN_LEASE',
        'CREDIT_REPORT': 'CREDIT_REPORTING',
        'CREDITREPORTING': 'CREDIT_REPORTING',
        'MONEY_TRANSFER_VIRTUAL_CURRENCY': 'MONEY_TRANSFER',
        'MONEYTRANSFER': 'MONEY_TRANSFER',
        'VEHICLELOANLEASE': 'VEHICLE_LOAN_LEASE',
    }
    squash = token.replace('_', '')
    return aliases.get(squash, aliases.get(token, token))


def _normalize_severity(value: str) -> str:
    return value.strip().upper()


def _normalize_issue(value: str) -> str:
    """Allow LLM to return either the enum NAME or the display VALUE."""
    stripped = value.strip()
    # Try display value first (StrEnum lookup by value)
    for member in IssueType:
        if member.value.lower() == stripped.lower():
            return member.value
    # Try enum name
    upper = stripped.upper().replace(' ', '_').replace('-', '_')
    for member in IssueType:
        if member.name == upper:
            return member.value
    # Return as-is and let Pydantic raise ValidationError
    return stripped


# ---------------------------------------------------------------------------
# Stage-1: Product classification result
# ---------------------------------------------------------------------------

class ProductClassificationResult(BaseModel):
    """Output of the first-stage product classifier agent."""

    model_config = ConfigDict(extra='ignore')

    product: ProductType
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str = Field(default='')

    @field_validator('product', mode='before')
    @classmethod
    def _normalise_product(cls, value: object) -> object:
        if isinstance(value, str):
            return _normalize_product_token(value)
        return value


# ---------------------------------------------------------------------------
# Stage-2: Issue classification result (conditioned on product)
# ---------------------------------------------------------------------------

class IssueClassificationResult(BaseModel):
    """Output of the second-stage issue classifier agent."""

    model_config = ConfigDict(extra='ignore')

    issue: IssueType
    severity: SeverityLevel
    compliance_risk: ComplianceRisk
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str = Field(default='')

    @field_validator('issue', mode='before')
    @classmethod
    def _normalise_issue(cls, value: object) -> object:
        if isinstance(value, str):
            return _normalize_issue(value)
        return value

    @field_validator('severity', 'compliance_risk', mode='before')
    @classmethod
    def _normalise_enums(cls, value: object) -> object:
        if isinstance(value, str):
            return _normalize_severity(value)
        return value

    def to_classification_result(
        self, product: ProductType
    ) -> 'ClassificationResult':
        """Merge with product to produce the pipeline-wide ClassificationResult."""
        return ClassificationResult(
            product_type=product,
            issue_type=self.issue,
            severity=self.severity,
            compliance_risk=self.compliance_risk,
            confidence=self.confidence,
        )


# ---------------------------------------------------------------------------
# Combined result (backward-compatible, consumed by all downstream agents)
# ---------------------------------------------------------------------------

class ClassificationResult(BaseModel):
    model_config = ConfigDict(extra='forbid')

    product_type: ProductType
    issue_type: IssueType
    severity: SeverityLevel
    compliance_risk: ComplianceRisk
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator('product_type', mode='before')
    @classmethod
    def _normalise_product(cls, value: object) -> object:
        if isinstance(value, str):
            return _normalize_product_token(value)
        return value

    @field_validator('issue_type', mode='before')
    @classmethod
    def _normalise_issue(cls, value: object) -> object:
        if isinstance(value, str):
            return _normalize_issue(value)
        return value

    @field_validator('severity', 'compliance_risk', mode='before')
    @classmethod
    def _normalise_severity(cls, value: object) -> object:
        if isinstance(value, str):
            return _normalize_severity(value)
        return value
