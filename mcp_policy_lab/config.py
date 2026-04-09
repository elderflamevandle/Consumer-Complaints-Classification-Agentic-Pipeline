from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class LabConfig:
    govinfo_mcp_url: str
    govinfo_api_key: str
    open_legal_codes_base_url: str
    serper_url: str
    serper_api_key: str
    timeout_seconds: float


def load_config(*, root: Path) -> LabConfig:
    _load_dotenv_if_present(root / ".env")
    timeout_text = os.getenv("HTTP_TIMEOUT_SECONDS", "20")
    try:
        timeout_seconds = float(timeout_text)
    except ValueError:
        timeout_seconds = 20.0

    return LabConfig(
        govinfo_mcp_url=os.getenv("GOVINFO_MCP_URL", "https://api.govinfo.gov/mcp"),
        govinfo_api_key=os.getenv("GOVINFO_API_KEY", ""),
        open_legal_codes_base_url=os.getenv(
            "OPEN_LEGAL_CODES_BASE_URL", "https://openlegalcodes.org/api/v1"
        ),
        serper_url=os.getenv("SERPER_URL", "https://google.serper.dev/search"),
        serper_api_key=os.getenv("SERPER_API_KEY", ""),
        timeout_seconds=timeout_seconds,
    )


def _load_dotenv_if_present(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key and key not in os.environ:
            os.environ[key] = value

