"""Tests for MCP server _normalize_issue function and expanded regulation lookups."""
from __future__ import annotations

from mcp_server.server import _normalize_issue, get_sla_requirements


def test_normalize_strips_apostrophe() -> None:
    result = _normalize_issue("Problem with a company's investigation into an existing problem")
    assert result == "PROBLEM_WITH_A_COMPANYS_INVESTIGATION_INTO_AN_EXISTING_PROBLEM"
    assert "'" not in result


def test_normalize_strips_comma() -> None:
    result = _normalize_issue("Advertising and marketing, including promotional offers")
    assert result == "ADVERTISING_AND_MARKETING_INCLUDING_PROMOTIONAL_OFFERS"
    assert "," not in result


def test_normalize_strips_comma_in_managing_opening() -> None:
    result = _normalize_issue("Managing, opening, or closing your mobile wallet account")
    assert result == "MANAGING_OPENING_OR_CLOSING_YOUR_MOBILE_WALLET_ACCOUNT"


def test_normalize_strips_comma_in_overdraft() -> None:
    result = _normalize_issue("Overdraft, savings, or rewards features")
    assert result == "OVERDRAFT_SAVINGS_OR_REWARDS_FEATURES"


def test_normalize_idempotent() -> None:
    key = "CREDIT_CARD"
    assert _normalize_issue(key) == key


def test_normalize_empty_string() -> None:
    assert _normalize_issue("") == ""


def test_fraud_issue_returns_10_day_sla() -> None:
    result = get_sla_requirements(issue_type="Fraud or scam", state_code="TX")
    assert result["sla_window"] == "10 calendar days"
    assert "FRAUD_OR_SCAM" == result["issue_type"]


def test_billing_issue_returns_21_day_sla() -> None:
    result = get_sla_requirements(issue_type="Fees or interest", state_code="TX")
    assert result["sla_window"] == "21 calendar days"


def test_credit_reporting_issue_returns_fcra_basis() -> None:
    result = get_sla_requirements(issue_type="Incorrect information on your report", state_code="TX")
    assert "FCRA" in result["regulatory_basis"]


def test_debt_collection_issue_returns_fdcpa_basis() -> None:
    result = get_sla_requirements(issue_type="Attempts to collect debt not owed", state_code="TX")
    assert "FDCPA" in result["regulatory_basis"]


def test_unauthorized_transactions_returns_fraud_sla() -> None:
    result = get_sla_requirements(
        issue_type="Unauthorized transactions or other transaction problem", state_code="TX"
    )
    assert result["sla_window"] == "10 calendar days"


def test_billing_ca_override_returns_15_day_sla() -> None:
    result = get_sla_requirements(issue_type="Fees or interest", state_code="CA")
    assert result["sla_window"] == "15 calendar days"


def test_fraud_ny_override_returns_7_day_sla() -> None:
    result = get_sla_requirements(issue_type="Fraud or scam", state_code="NY")
    assert result["sla_window"] == "7 calendar days"


def test_general_issue_returns_default_30_day_sla() -> None:
    result = get_sla_requirements(issue_type="Closing an account", state_code="TX")
    assert result["sla_window"] == "30 calendar days"
