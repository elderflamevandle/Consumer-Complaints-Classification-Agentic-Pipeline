"""Build search queries from state, product, and issue strings."""

from __future__ import annotations

from legal_knowledge_mcp.normalize import normalize_issue


def issue_label(issue_type: str) -> str:
    """Human-ish label from raw or normalized issue text."""
    key = normalize_issue(issue_type)
    if not key:
        return issue_type.strip()
    return key.replace('_', ' ').strip().lower()


def govinfo_query(*, state_code: str, product_token: str | None, issue_type: str) -> str:
    """Federal search: USC/CFR-oriented terms plus product/issue context."""
    st = state_code.strip().upper()
    prod = (product_token or 'consumer financial').replace('_', ' ').lower()
    issue = issue_label(issue_type)
    return (
        f'("{issue}" OR consumer OR credit OR banking) AND '
        f'({prod} OR "truth in lending" OR "electronic fund transfer" OR '
        f'"fair credit reporting" OR "equal credit opportunity" OR FDCPA OR FCRA OR TILA OR EFTA OR REG Z OR REG E) '
        f'AND (United States OR CFR OR USC OR "Code of Federal Regulations")'
    )


def open_states_query(*, product_token: str | None, issue_type: str) -> str:
    """State bill full-text search."""
    prod = (product_token or 'consumer').replace('_', ' ').lower()
    issue = issue_label(issue_type)
    return f'{issue} {prod} credit debt mortgage insurance financial consumer'


def state_jurisdiction_id(state_code: str) -> str:
    """OCD jurisdiction id for a US state (two-letter code)."""
    s = state_code.strip().lower()
    if len(s) != 2 or not s.isalpha():
        raise ValueError('state_code must be a two-letter US state code')
    return f'ocd-jurisdiction/country:us/state:{s}/government'
