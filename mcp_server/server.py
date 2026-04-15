"""Backward-compatible entrypoint; implementation is in ``legal_knowledge_mcp``."""

from __future__ import annotations

from legal_knowledge_mcp.bridge import get_sla_requirements
from legal_knowledge_mcp.normalize import normalize_issue as _normalize_issue
from legal_knowledge_mcp.server import (
    TOOL_GET_SLA,
    TOOL_LIST,
    TOOL_SEARCH,
    handle_request,
    main,
)

__all__ = [
    'TOOL_GET_SLA',
    'TOOL_LIST',
    'TOOL_SEARCH',
    '_normalize_issue',
    'get_sla_requirements',
    'handle_request',
    'main',
]

if __name__ == '__main__':
    raise SystemExit(main())
