"""Compliance bridge: live GovInfo + Open States by default; mock JSON only when opted in."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from legal_knowledge_mcp.compliance_live import api_keys_configured, build_live_policy, use_mock_fallback
from legal_knowledge_mcp.normalize import normalize_issue
from legal_knowledge_mcp.policy_store import build_base_policy, regulations_path_default


def get_sla_requirements(
    *,
    issue_type: str,
    state_code: str,
    product_type: str | None = None,
    regulations_path: Path | None = None,
    enrich_citations: bool = True,
) -> dict[str, Any]:
    """Return SLA-shaped policy fields.

    **Default (production):** queries GovInfo (federal) and Open States (state bills) using
    API keys from the environment. Results are ranked by simple keyword overlap with your
    product/issue — not a legal determination.

    **Offline tests / no network:** set ``LEGAL_MCP_USE_MOCK_FALLBACK=1`` to use
    ``mcp_server/mock_regulations.json`` instead.

    ``enrich_citations`` is ignored for live mode; kept for call compatibility.
    """
    _ = enrich_citations
    if use_mock_fallback():
        return _from_mock_dataset(
            issue_type=issue_type,
            state_code=state_code,
            product_type=product_type,
            regulations_path=regulations_path,
        )

    try:
        if not api_keys_configured():
            raise ValueError(
                'Live compliance mode requires API keys. Set GOVINFO_API_KEY or DATA_GOV_API_KEY '
                'and/or OPEN_STATES_API_KEY, or set LEGAL_MCP_USE_MOCK_FALLBACK=1 for offline mock data.'
            )

        return build_live_policy(
            issue_type=issue_type,
            state_code=state_code,
            product_type=product_type,
        )
    except Exception as e:
        import sys
        print(f"⚠️ Live policy retrieval failed ({e}). Falling back to mock dataset...", file=sys.stderr)
        return _from_mock_dataset(
            issue_type=issue_type,
            state_code=state_code,
            product_type=product_type,
            regulations_path=regulations_path,
        )


def _from_mock_dataset(
    *,
    issue_type: str,
    state_code: str,
    product_type: str | None,
    regulations_path: Path | None,
) -> dict[str, Any]:
    base = build_base_policy(
        issue_type=issue_type,
        state_code=state_code,
        regulations_path=regulations_path,
    )
    product_token = _normalize_product(product_type)
    legal_citations: list[dict[str, str]] = [
        {
            'title': 'Local policy norms dataset (mock / simulation)',
            'url': 'file://mcp_server/mock_regulations.json',
            'publisher': 'FinComplaint AI (offline fallback)',
            'note': 'LEGAL_MCP_USE_MOCK_FALLBACK is enabled; not live law.',
            'layer': 'mock',
        }
    ]
    if api_keys_configured():
        from legal_knowledge_mcp.query_builder import govinfo_query, open_states_query
        from legal_knowledge_mcp.sources.govinfo_client import fetch_govinfo_citations
        from legal_knowledge_mcp.sources.open_states_client import fetch_open_states_bills

        st = base['state_code']
        issue_key = base['issue_type']
        q_gov = govinfo_query(state_code=st, product_token=product_token, issue_type=issue_type)
        q_os = open_states_query(product_token=product_token, issue_type=issue_type)
        legal_citations.extend(fetch_govinfo_citations(query=q_gov))
        legal_citations.extend(fetch_open_states_bills(state_code=st, query=q_os))

    return {
        **base,
        'product_type': product_token,
        'legal_citations': legal_citations[:25],
        'source': 'mock_fallback',
    }


def search_state_regulations(
    *,
    state: str,
    product_category: str,
    issue_code: str,
    regulations_path: Path | None = None,
) -> dict[str, Any]:
    """Router tool: state + product + issue → same contract as ``get_sla_requirements``."""
    state_code = state.strip().upper()
    merged = get_sla_requirements(
        issue_type=issue_code,
        state_code=state_code,
        product_type=product_category,
        regulations_path=regulations_path or regulations_path_default(),
    )
    return {
        'state': merged['state_code'],
        'product_category': merged.get('product_type'),
        'issue_code': merged['issue_type'],
        'sla_window': merged['sla_window'],
        'required_actions': merged['required_actions'],
        'regulatory_basis': merged['regulatory_basis'],
        'legal_citations': merged.get('legal_citations', []),
        'source': merged.get('source', 'unknown'),
        'search_queries': merged.get('search_queries'),
        'disclaimer': (
            'Informational retrieval only; not legal advice. '
            'Verify every obligation in the cited official sources.'
        ),
    }


def _normalize_product(product_type: str | None) -> str | None:
    if not product_type:
        return None
    token = product_type.strip().upper().replace('-', '_').replace(' ', '_')
    token = ''.join(c for c in token if c.isalnum() or c == '_')
    return token or None
