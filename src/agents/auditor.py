"""Auditor agent for compliance review of customer-facing drafts."""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import ValidationError

from src.agents.prompts import build_auditor_prompt, build_auditor_repair_prompt, get_policy_labels
from src.agents.remediator import RemediationResult
from src.llm.client import GroqLLMClient
from src.schemas.auditor import AuditReasonCode, AuditVerdict, ResponseAuditResult
from src.schemas.response import ResponseDraft
from src.tools.audit_logger import AuditLogger

SCHEMA_REPAIR_RETRIES = 1
_OVERCOMMITMENT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r'\bguarantee\b', re.IGNORECASE),
    re.compile(r'\bliable\b', re.IGNORECASE),
    re.compile(r'\bour fault\b', re.IGNORECASE),
    re.compile(r'\bpromise\b', re.IGNORECASE),
    re.compile(r'\bdefinitely\b', re.IGNORECASE),
)
_UNSAFE_TONE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r'\bcalm down\b', re.IGNORECASE),
    re.compile(r'\bobviously\b', re.IGNORECASE),
    re.compile(r'\byou must\b', re.IGNORECASE),
)
_FIX_INSTRUCTIONS: dict[AuditReasonCode, str] = {
    AuditReasonCode.MISSING_POLICY_CITATION: (
        'Include the required policy citation labels in the findings block.'
    ),
    AuditReasonCode.UNSAFE_TONE: (
        'Rewrite the response in a calm, professional, customer-safe tone.'
    ),
    AuditReasonCode.OVERCOMMITMENT: (
        'Remove any guaranteed outcomes or liability-admission language.'
    ),
    AuditReasonCode.STRUCTURE_MISSING: (
        'Restore the fixed four-block response structure and required fields.'
    ),
    AuditReasonCode.UNCLEAR_RESOLUTION: 'State the resolution path clearly in the findings block.',
}


class AuditorAgent:
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

    def review_response(
        self,
        *,
        draft: ResponseDraft,
        remediation: RemediationResult,
        thread_id: str | None = None,
    ) -> ResponseAuditResult:
        prompt = self._build_prompt(draft=draft, remediation=remediation)
        self.used_fallback = False

        for attempt in range(self.repair_retries + 1):
            try:
                response = self._client.complete(
                    prompt=prompt,
                    agent_name='auditor',
                    critical=True,
                    max_tokens=420,
                )
            except Exception:
                break

            self.last_model = response.model
            parsed = self._parse_or_none(response.text)
            if parsed is not None:
                normalized = self._merge_with_heuristics(
                    parsed=parsed,
                    draft=draft,
                    remediation=remediation,
                )
                decision = (
                    'audit_pass'
                    if normalized.verdict == AuditVerdict.PASS
                    else 'audit_fail'
                )
                self._log_outcome(
                    thread_id=thread_id,
                    model=response.model,
                    decision=decision,
                    scrubbed_text=draft.render_text(),
                )
                return normalized
            if attempt < self.repair_retries:
                prompt = self._repair_prompt(draft=draft, remediation=remediation)

        self.used_fallback = True
        fallback = self._heuristic_review(draft=draft, remediation=remediation)
        self._log_outcome(
            thread_id=thread_id,
            model='auditor-fallback',
            decision='audit_pass' if fallback.verdict == AuditVerdict.PASS else 'audit_fail',
            scrubbed_text=draft.render_text(),
        )
        return fallback

    def _build_prompt(self, *, draft, remediation) -> str:
        return build_auditor_prompt(draft=draft, remediation=remediation)

    def _repair_prompt(self, *, draft, remediation) -> str:
        return build_auditor_repair_prompt(draft=draft, remediation=remediation)

    def _parse_or_none(self, text: str) -> ResponseAuditResult | None:
        candidate = _extract_json_object(text)
        if candidate is None:
            return None
        try:
            return ResponseAuditResult.model_validate_json(candidate)
        except (ValidationError, json.JSONDecodeError, ValueError):
            return None

    def _merge_with_heuristics(
        self,
        *,
        parsed: ResponseAuditResult,
        draft: ResponseDraft,
        remediation: RemediationResult,
    ) -> ResponseAuditResult:
        heuristic = self._heuristic_review(draft=draft, remediation=remediation)
        if heuristic.verdict == AuditVerdict.PASS:
            return parsed

        merged_codes = list(dict.fromkeys([*parsed.reason_codes, *heuristic.reason_codes]))
        merged_fixes = list(dict.fromkeys([*parsed.must_fix_items, *heuristic.must_fix_items]))
        return ResponseAuditResult(
            verdict=AuditVerdict.FAIL,
            reason_codes=merged_codes,
            critique_summary=heuristic.critique_summary,
            must_fix_items=merged_fixes,
            rewrite_recommended=True,
        )

    def _heuristic_review(
        self,
        *,
        draft: ResponseDraft,
        remediation: RemediationResult,
    ) -> ResponseAuditResult:
        reason_codes: list[AuditReasonCode] = []
        rendered = draft.render_text()
        lowered = rendered.lower()

        if not all(
            [
                draft.acknowledgment.strip(),
                draft.findings.strip(),
                draft.action_steps,
                draft.timeline_next_steps.strip(),
            ]
        ):
            reason_codes.append(AuditReasonCode.STRUCTURE_MISSING)

        expected_labels = get_policy_labels(remediation)
        if expected_labels and not set(expected_labels).issubset(set(draft.policy_citation_labels)):
            reason_codes.append(AuditReasonCode.MISSING_POLICY_CITATION)

        if (
            len(draft.resolution_statement.split()) < 4
            or lowered.startswith('acknowledgment:\npending')
        ):
            reason_codes.append(AuditReasonCode.UNCLEAR_RESOLUTION)

        if any(pattern.search(rendered) for pattern in _OVERCOMMITMENT_PATTERNS):
            reason_codes.append(AuditReasonCode.OVERCOMMITMENT)

        if any(pattern.search(rendered) for pattern in _UNSAFE_TONE_PATTERNS):
            reason_codes.append(AuditReasonCode.UNSAFE_TONE)

        if not reason_codes:
            return ResponseAuditResult(
                verdict=AuditVerdict.PASS,
                reason_codes=[],
                critique_summary=(
                    'Response satisfies structure, policy-grounding, and customer-safe tone checks.'
                ),
                must_fix_items=[],
                rewrite_recommended=False,
            )

        must_fix_items = [_FIX_INSTRUCTIONS[code] for code in reason_codes]
        return ResponseAuditResult(
            verdict=AuditVerdict.FAIL,
            reason_codes=reason_codes,
            critique_summary=(
                'Revise the response to address the identified compliance and clarity issues.'
            ),
            must_fix_items=must_fix_items,
            rewrite_recommended=True,
        )

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
            node='auditor',
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
