"""Tests for MCP server _normalize_issue function and expanded regulation lookups."""
from __future__ import annotations

import pytest

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


def test_search_state_regulations_tool_returns_bundle() -> None:
    from legal_knowledge_mcp.server import handle_request

    out = handle_request(
        {
            "tool": "search_state_regulations",
            "arguments": {
                "state": "CA",
                "product_category": "CREDIT_CARD",
                "issue_code": "Fees or interest",
            },
        }
    )
    assert out["status"] == "ok"
    body = out["result"]
    assert body["state"] == "CA"
    assert body["issue_code"] == "FEES_OR_INTEREST"
    assert "legal_citations" in body
    assert body.get("disclaimer")
    assert body.get("source") == "mock_fallback"


def test_live_mode_requires_api_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    from legal_knowledge_mcp.bridge import get_sla_requirements

    monkeypatch.setenv("LEGAL_MCP_USE_MOCK_FALLBACK", "0")
    for key in ("GOVINFO_API_KEY", "DATA_GOV_API_KEY", "OPEN_STATES_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    try:
        get_sla_requirements(issue_type="Fees or interest", state_code="TX")
    except ValueError as exc:
        assert "Live compliance mode requires API keys" in str(exc)
    else:
        raise AssertionError("expected ValueError when live mode has no API keys")
