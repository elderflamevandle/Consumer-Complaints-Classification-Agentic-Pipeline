"""Writer agent for customer-facing complaint responses."""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import ValidationError

from src.agents.prompts import build_writer_prompt, build_writer_repair_prompt, get_policy_labels
from src.agents.remediator import RemediationResult
from src.llm.client import GroqLLMClient
from src.schemas.classification import ClassificationResult
from src.schemas.response import ResponseDraft
from src.schemas.root_cause import RootCauseResult
from src.tools.audit_logger import AuditLogger

SCHEMA_REPAIR_RETRIES = 1
_GUARDRAIL_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r'\bwe guarantee\b', re.IGNORECASE), 'we will work'),
    (re.compile(r'\bguaranteed\b', re.IGNORECASE), 'expected'),
    (re.compile(r'\byou will definitely\b', re.IGNORECASE), 'we will aim to'),
    (re.compile(r'\bdefinitely\b', re.IGNORECASE), 'carefully'),
    (re.compile(r'\bwe are liable\b', re.IGNORECASE), 'we take this concern seriously'),
    (re.compile(r'\badmit liability\b', re.IGNORECASE), 'address the concern'),
    (re.compile(r'\bour fault\b', re.IGNORECASE), 'the issue you reported'),
    (re.compile(r'\bpromise\b', re.IGNORECASE), 'plan'),
)


class WriterAgent:
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
        self.guardrail_triggered = False
        self.last_total_tokens = 0
        self.last_llm_attempts = 0

    def compose_response(
        self,
        *,
        complaint_text: str,
        classification: ClassificationResult,
        diagnosis: RootCauseResult,
        remediation: RemediationResult,
        unresolved_issues: list[str] | None = None,
        thread_id: str | None = None,
    ) -> ResponseDraft:
        issues = list(unresolved_issues or [])
        prompt = self._build_prompt(
            complaint_text=complaint_text,
            classification=classification,
            diagnosis=diagnosis,
            remediation=remediation,
            unresolved_issues=issues,
        )
        self.used_fallback = False
        self.guardrail_triggered = False
        self.last_total_tokens = 0
        self.last_llm_attempts = 0

        raw_output = ''
        for attempt in range(self.repair_retries + 1):
            self.last_llm_attempts += 1
            response = self._client.complete(
                prompt=prompt,
                agent_name='writer',
                critical=True,
                max_tokens=520,
            )
            self.last_model = response.model
            self.last_total_tokens += response.total_tokens
            raw_output = response.text
            parsed = self._parse_or_none(raw_output)
            if parsed is not None:
                drafted, sanitized = self._apply_guardrails(
                    parsed,
                    remediation=remediation,
                    unresolved_issues=issues,
                )
                self.guardrail_triggered = sanitized
                decision = (
                    'response_draft_guardrail_sanitized'
                    if sanitized
                    else 'response_draft_generated'
                )
                self._log_outcome(
                    thread_id=thread_id,
                    model=response.model,
                    decision=decision,
                    scrubbed_text=complaint_text,
                )
                return drafted
            if attempt < self.repair_retries:
                prompt = self._repair_prompt(
                    complaint_text=complaint_text,
                    classification=classification,
                    diagnosis=diagnosis,
                    remediation=remediation,
                    unresolved_issues=issues,
                    invalid_output=raw_output,
                )

        self.used_fallback = True
        fallback = self._fallback_draft(
            complaint_text=complaint_text,
            classification=classification,
            diagnosis=diagnosis,
            remediation=remediation,
            unresolved_issues=issues,
        )
        self._log_outcome(
            thread_id=thread_id,
            model='writer-fallback',
            decision='response_draft_fallback',
            scrubbed_text=complaint_text,
        )
        return fallback

    def _build_prompt(
        self,
        *,
        complaint_text: str,
        classification,
        diagnosis,
        remediation,
        unresolved_issues: list[str],
    ) -> str:
        return build_writer_prompt(
            complaint_text=complaint_text,
            classification=classification,
            diagnosis=diagnosis,
            remediation=remediation,
            unresolved_issues=unresolved_issues,
        )

    def _repair_prompt(
        self,
        *,
        complaint_text: str,
        classification,
        diagnosis,
        remediation,
        unresolved_issues: list[str],
        invalid_output: str,
    ) -> str:
        return build_writer_repair_prompt(
            complaint_text=complaint_text,
            classification=classification,
            diagnosis=diagnosis,
            remediation=remediation,
            unresolved_issues=unresolved_issues,
            invalid_output=invalid_output,
        )

    def _parse_or_none(self, text: str) -> ResponseDraft | None:
        candidate = _extract_json_object(text)
        if candidate is None:
            return None
        try:
            return ResponseDraft.model_validate_json(candidate)
        except (ValidationError, json.JSONDecodeError):
            return None

    def _apply_guardrails(
        self,
        draft: ResponseDraft,
        *,
        remediation: RemediationResult,
        unresolved_issues: list[str],
    ) -> tuple[ResponseDraft, bool]:
        sanitized = False
        updated = draft.model_dump()

        text_fields = (
            'resolution_statement',
            'acknowledgment',
            'findings',
            'timeline_next_steps',
        )
        for field_name in text_fields:
            original = str(updated[field_name])
            cleaned = _sanitize_text(original)
            if cleaned != original:
                sanitized = True
                updated[field_name] = cleaned

        sanitized_steps: list[str] = []
        for item in list(updated['action_steps']):
            cleaned = _sanitize_text(item)
            if cleaned != item:
                sanitized = True
            sanitized_steps.append(cleaned)
        updated['action_steps'] = sanitized_steps

        labels = list(updated.get('policy_citation_labels') or [])
        if not labels:
            labels = get_policy_labels(remediation)
            if labels:
                sanitized = True
        updated['policy_citation_labels'] = labels

        if unresolved_issues:
            updated['critique_items_addressed'] = list(dict.fromkeys(unresolved_issues))
        elif not updated.get('critique_items_addressed'):
            updated['critique_items_addressed'] = []

        return ResponseDraft.model_validate(updated), sanitized

    def _fallback_draft(
        self,
        *,
        complaint_text: str,
        classification: ClassificationResult,
        diagnosis: RootCauseResult,
        remediation: RemediationResult,
        unresolved_issues: list[str],
    ) -> ResponseDraft:
        issue_text = classification.issue_type.value.lower()
        product_text = classification.product_type.value.lower().replace('_', ' ')
        actions = [step.action for step in remediation.action_plan] or [
            'Review the information already provided and confirm the next required action.',
            'Share any additional documentation requests in writing before further review.',
        ]
        sla_window = str(
            remediation.policy_citations.get('sla_window', 'the required review window')
        )
        findings = (
            f'Current findings point to {diagnosis.root_cause.rstrip(".")}. '
            f'This response addresses your reported {issue_text} concern on the '
            f'{product_text} account.'
        )
        if unresolved_issues:
            findings += f' This revision specifically addresses: {"; ".join(unresolved_issues)}.'
        return ResponseDraft(
            resolution_statement=(
                f'We will review your {issue_text} concern using the applicable '
                'complaint-resolution steps.'
            ),
            acknowledgment=(
                'We understand the concern described in your complaint and appreciate '
                'the chance to review it.'
            ),
            findings=findings,
            action_steps=actions,
            timeline_next_steps=(
                f'We will follow up within {sla_window} with the next status update or '
                'any additional information needed.'
            ),
            policy_citation_labels=get_policy_labels(remediation),
            critique_items_addressed=list(dict.fromkeys(unresolved_issues)),
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
            node='writer',
            model=model,
            latency_ms=0,
            decision=decision,
            scrubbed_text=scrubbed_text[:220],
        )


def _sanitize_text(text: str) -> str:
    cleaned = text
    for pattern, replacement in _GUARDRAIL_PATTERNS:
        cleaned = pattern.sub(replacement, cleaned)
    return ' '.join(cleaned.split())


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
