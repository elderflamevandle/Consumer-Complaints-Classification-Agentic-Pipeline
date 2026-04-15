"""Pytest defaults: use offline mock regulations unless running live API integration tests."""

from __future__ import annotations

import os


def pytest_configure(config: object) -> None:
    # Live mode hits GovInfo/Open States and needs real keys + network.
    if os.environ.get('LIVE_MCP_INTEGRATION') == '1':
        return
    os.environ.setdefault('LEGAL_MCP_USE_MOCK_FALLBACK', '1')
