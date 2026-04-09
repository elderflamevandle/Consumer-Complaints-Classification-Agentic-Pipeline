from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from mcp_policy_lab.config import load_config
from mcp_policy_lab.providers import (
    DummyPolicyProvider,
    GovInfoMCPProvider,
    OpenLegalCodesProvider,
    SerperSearchProvider,
)
from mcp_policy_lab.policy_models import PolicyProvider, PolicyRequest, PolicyResult


@dataclass(slots=True)
class ResolverTrace:
    provider: str
    success: bool
    message: str


@dataclass(slots=True)
class ResolverOutput:
    result: PolicyResult | None
    traces: list[ResolverTrace]


class PolicyResolver:
    def __init__(self, providers: list[PolicyProvider]) -> None:
        self.providers = providers

    def resolve(self, request: PolicyRequest) -> ResolverOutput:
        traces: list[ResolverTrace] = []
        for provider in self.providers:
            try:
                result = provider.resolve(request)
            except Exception as error:  # pragma: no cover - defensive path
                traces.append(
                    ResolverTrace(
                        provider=provider.name,
                        success=False,
                        message=f"error: {error}",
                    )
                )
                continue

            if result is None:
                traces.append(
                    ResolverTrace(
                        provider=provider.name,
                        success=False,
                        message="no_match",
                    )
                )
                continue

            traces.append(
                ResolverTrace(
                    provider=provider.name,
                    success=True,
                    message="resolved",
                )
            )
            return ResolverOutput(result=result, traces=traces)

        return ResolverOutput(result=None, traces=traces)


def build_default_resolver(*, root: Path) -> PolicyResolver:
    config = load_config(root=root)
    providers: list[PolicyProvider] = [
        DummyPolicyProvider(path=root / "dummy_policy_rules.json"),
        GovInfoMCPProvider(
            mcp_url=config.govinfo_mcp_url,
            api_key=config.govinfo_api_key,
            timeout_seconds=config.timeout_seconds,
        ),
        OpenLegalCodesProvider(
            base_url=config.open_legal_codes_base_url,
            timeout_seconds=config.timeout_seconds,
        ),
        SerperSearchProvider(
            url=config.serper_url,
            api_key=config.serper_api_key,
            timeout_seconds=config.timeout_seconds,
        ),
    ]
    return PolicyResolver(providers=providers)

