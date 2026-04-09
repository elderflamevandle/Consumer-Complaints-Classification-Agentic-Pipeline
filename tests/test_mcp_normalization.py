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
