"""Remediator agent that grounds action plans in MCP policy requirements."""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from src.agents.prompts import build_remediator_prompt
from src.llm.client import GroqLLMClient
from src.schemas.classification import ClassificationResult
from src.schemas.root_cause import RootCauseResult
from src.tools.audit_logger import AuditLogger
from src.tools.mcp_policy_client import MCPPolicyClient, PolicyLookupResult


class RemediationStep(BaseModel):
    model_config = ConfigDict(extra='forbid')

    order: int = Field(ge=1)
    action: str = Field(min_length=1)
    policy_reference: str = Field(min_length=1)


class RemediationResult(BaseModel):
    model_config = ConfigDict(extra='forbid')

    status: str
    route: str
    action_plan: list[RemediationStep] = Field(default_factory=list)
    policy_citations: dict[str, Any] = Field(default_factory=dict)


class _ModelPlan(BaseModel):
    model_config = ConfigDict(extra='forbid')

    action_plan: list[str] = Field(min_length=1)


class RemediatorAgent:
    def __init__(
        self,
        *,
        llm_client: GroqLLMClient | None = None,
        transport: Any | None = None,
        mcp_client: MCPPolicyClient | None = None,
        audit_logger: AuditLogger | None = None,
    ) -> None:
        self._client = llm_client or GroqLLMClient(transport=transport)
        self._mcp = mcp_client or MCPPolicyClient()
        self._audit_logger = audit_logger
        self.call_order: list[str] = []
        self.last_model: str | None = None

    def propose_action(
        self,
        *,
        complaint_text: str,
        classification: ClassificationResult,
        diagnosis: RootCauseResult,
        state_code: str,
        thread_id: str | None = None,
    ) -> RemediationResult:
        self.call_order = []
        self.call_order.append('mcp')
        policy_result = self._mcp.get_sla_requirements(
            issue_type=classification.issue_type.value,
            state_code=state_code,
            product_type=classification.product_type.value,
        )
        if not policy_result.available:
            result = RemediationResult(
                status='POLICY_UNAVAILABLE',
                route='human_review',
                action_plan=[],
                policy_citations={},
            )
            self._log_outcome(
                thread_id=thread_id,
                model='mcp-policy-gate',
                decision='policy_unavailable',
                scrubbed_text=complaint_text,
            )
            return result

        policy = policy_result.policy
        assert policy is not None

        self.call_order.append('llm')
        response = self._client.complete(
            prompt=self._build_prompt(
                complaint_text=complaint_text,
                classification=classification,
                diagnosis=diagnosis,
                policy=policy_result,
            ),
            agent_name='remediator',
            critical=True,
            max_tokens=420,
        )
        self.last_model = response.model

        model_actions = self._parse_actions_or_none(response.text)
        if model_actions is None:
            model_actions = list(policy.required_actions)

        steps: list[RemediationStep] = []
        for index, action in enumerate(model_actions, start=1):
            steps.append(
                RemediationStep(
                    order=index,
                    action=action,
                    policy_reference=policy.regulatory_basis,
                )
            )

        citations: dict[str, Any] = {
            'sla_window': policy.sla_window,
            'required_actions': list(policy.required_actions),
            'regulatory_basis': policy.regulatory_basis,
            'product_type': policy.product_type,
            'legal_citations': list(policy.legal_citations),
        }
        result = RemediationResult(
            status='ok',
            route='continue',
            action_plan=steps,
            policy_citations=citations,
        )
        self._log_outcome(
            thread_id=thread_id,
            model=response.model,
            decision='policy_grounded_action_plan',
            scrubbed_text=complaint_text,
        )
        return result

    def _build_prompt(
        self,
        *,
        complaint_text: str,
        classification,
        diagnosis,
        policy,
    ) -> str:
        return build_remediator_prompt(
            complaint_text=complaint_text,
            classification=classification,
            diagnosis=diagnosis,
            policy=policy,
        )

    def _parse_actions_or_none(self, text: str) -> list[str] | None:
        candidate = _extract_json_object(text)
        if candidate is None:
            return None
        try:
            parsed = _ModelPlan.model_validate_json(candidate)
        except (ValidationError, json.JSONDecodeError):
            return None
        return [item.strip() for item in parsed.action_plan if item.strip()]

    def _log_outcome(
        self,
        *,
        thread_id: str | None,
        model: str,
        decision: str,
        scrubbed_text: str,
    ) -> None:
        if thread_id is None or self._audit_logger is None:
            return
        self._audit_logger.log_node_outcome(
            thread_id=thread_id,
            node='remediator',
            model=model,
            latency_ms=0,
            decision=decision,
            scrubbed_text=scrubbed_text[:220],
        )


def _extract_json_object(text: str) -> str | None:
    stripped = text.strip()
    if not stripped:
        return None

    if stripped.startswith('{') and stripped.endswith('}'):
        return stripped

    fenced = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', stripped, flags=re.DOTALL)
    if fenced:
        return fenced.group(1)

    any_json = re.search(r'(\{.*\})', stripped, flags=re.DOTALL)
    if any_json:
        return any_json.group(1)
    return None
