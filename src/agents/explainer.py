"""Explainer agent for deterministic stage-chain rationale summaries."""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import ValidationError

from src.agents.prompts import build_explainer_prompt, build_explainer_repair_prompt
from src.agents.remediator import RemediationResult
from src.llm.client import GroqLLMClient
from src.schemas.auditor import ResponseAuditResult
from src.schemas.classification import ClassificationResult
from src.schemas.explainer import ExplanationBullet, ExplanationResult
from src.schemas.response import ResponseDraft
from src.schemas.root_cause import RootCauseResult
from src.tools.audit_logger import AuditLogger

SCHEMA_REPAIR_RETRIES = 1


class ExplainerAgent:
    def __init__(
        self,
        *,
        llm_client: GroqLLMClient | None = None,
        transport: Any | None = None,
        repair_retries: int = SCHEMA_REPAIR_RETRIES,
        audit_logger: AuditLogger | None = None,
    ) -> None:
        self._client = llm_client or GroqLLMClient(transport=transport)
        self.repair_retries = repair_retries
        self._audit_logger = audit_logger
        self.last_model: str | None = None
        self.used_fallback = False
        self.last_total_tokens = 0
        self.last_llm_attempts = 0

    def summarize_chain(
        self,
        *,
        classification: ClassificationResult,
        diagnosis: RootCauseResult,
        remediation: RemediationResult,
        final_response: ResponseDraft,
        audit_verdict: ResponseAuditResult,
        raw_input: str | None = None,
        thread_id: str | None = None,
    ) -> ExplanationResult:
        del raw_input
        prompt = self._build_prompt(
            classification=classification,
            diagnosis=diagnosis,
            remediation=remediation,
            final_response=final_response,
            audit_verdict=audit_verdict,
        )
        self.used_fallback = False
        self.last_total_tokens = 0
        self.last_llm_attempts = 0

        for attempt in range(self.repair_retries + 1):
            try:
                self.last_llm_attempts += 1
                response = self._client.complete(
                    prompt=prompt,
                    agent_name='explainer',
                    critical=True,
                    max_tokens=420,
                )
            except Exception:
                break

            self.last_model = response.model
            self.last_total_tokens += response.total_tokens
            parsed = self._parse_or_none(response.text)
            if parsed is not None:
                normalized = self._normalize_result(parsed)
                self._log_outcome(
                    thread_id=thread_id,
                    model=response.model,
                    decision='explanation_generated',
                    scrubbed_text=normalized.render_text(),
                )
                return normalized
            if attempt < self.repair_retries:
                prompt = self._repair_prompt(
                    classification=classification,
                    diagnosis=diagnosis,
                    remediation=remediation,
                    final_response=final_response,
                    audit_verdict=audit_verdict,
                )

        self.used_fallback = True
        fallback = self._fallback_result(
            classification=classification,
            diagnosis=diagnosis,
            remediation=remediation,
            final_response=final_response,
            audit_verdict=audit_verdict,
        )
        self._log_outcome(
            thread_id=thread_id,
            model='explainer-fallback',
            decision='explanation_generated',
            scrubbed_text=fallback.render_text(),
        )
        return fallback

    def _build_prompt(
        self,
        *,
        classification,
        diagnosis,
        remediation,
        final_response,
        audit_verdict,
    ) -> str:
        return build_explainer_prompt(
            classification=classification,
            diagnosis=diagnosis,
            remediation=remediation,
            final_response=final_response,
            audit_verdict=audit_verdict,
        )

    def _repair_prompt(
        self,
        *,
        classification,
        diagnosis,
        remediation,
        final_response,
        audit_verdict,
    ) -> str:
        return build_explainer_repair_prompt(
            classification=classification,
            diagnosis=diagnosis,
            remediation=remediation,
            final_response=final_response,
            audit_verdict=audit_verdict,
        )

    def _parse_or_none(self, text: str) -> ExplanationResult | None:
        candidate = _extract_json_object(text)
        if candidate is None:
            return None
        try:
            return ExplanationResult.model_validate_json(candidate)
        except (ValidationError, json.JSONDecodeError):
            return None

    def _normalize_result(self, result: ExplanationResult) -> ExplanationResult:
        ordered_bullets = result.bullets[:7]
        if len(ordered_bullets) < 5:
            raise ValueError('Explanation requires at least five bullets')
        return ExplanationResult(bullets=ordered_bullets)

    def _fallback_result(
        self,
        *,
        classification: ClassificationResult,
        diagnosis: RootCauseResult,
        remediation: RemediationResult,
        final_response: ResponseDraft,
        audit_verdict: ResponseAuditResult,
    ) -> ExplanationResult:
        regulatory_basis = remediation.policy_citations.get(
            'regulatory_basis',
            'policy basis unavailable',
        )
        citations = [
            f'{item.citation.id}:{item.citation.issue}'
            for item in diagnosis.evidence[:2]
        ]
        bullets = [
            ExplanationBullet(
                stage='classification',
                summary=(
                    f'Classified the complaint as {classification.product_type.value} / '
                    f'{classification.issue_type.value} with confidence '
                    f'{classification.confidence:.2f}.'
                ),
                citations=[],
            ),
            ExplanationBullet(
                stage='diagnosis',
                summary=f'Diagnosis identified {diagnosis.root_cause}.',
                citations=citations,
            ),
            ExplanationBullet(
                stage='remediation',
                summary=(
                    f'Remediation produced {len(remediation.action_plan)} ordered action steps '
                    f'under {regulatory_basis}.'
                ),
                citations=[str(regulatory_basis)],
            ),
            ExplanationBullet(
                stage='response',
                summary=(
                    f'Writer generated draft mapping {len(final_response.internal.action_steps)} '
                    'remediation steps to policy outcomes. '
                    f'Final response states: {final_response.internal.resolution_summary} '
                    f'(SLA: {final_response.external.timeline})'
                ),
                citations=[remediation.action_plan[0].policy_reference] if remediation.action_plan else [],
            ),
            ExplanationBullet(
                stage='audit',
                summary=(
                    f'Audit verdict was {audit_verdict.verdict.value} with '
                    f'{len(audit_verdict.reason_codes)} outstanding reason codes.'
                ),
                citations=[code.value for code in audit_verdict.reason_codes],
            ),
        ]
        return ExplanationResult(bullets=bullets)

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
            node='explainer',
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
