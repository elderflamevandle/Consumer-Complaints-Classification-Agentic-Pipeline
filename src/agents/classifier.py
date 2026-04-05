"""Classifier agent with strict schema validation and bounded repair retries."""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import ValidationError

from src.llm.client import GroqLLMClient
from src.schemas.classification import (
    ClassificationResult,
    ComplianceRisk,
    IssueType,
    ProductType,
    SeverityLevel,
)
from src.schemas.intake import IntakePreparation

SCHEMA_REPAIR_RETRIES = 2


def keyword_score_confidence(text: str) -> float:
    lowered = text.lower()
    keyword_buckets = (
        ('fraud', 0.14),
        ('identity theft', 0.12),
        ('ssn', 0.12),
        ('chargeback', 0.1),
        ('charged', 0.08),
        ('billing', 0.08),
        ('lawsuit', 0.1),
        ('harassment', 0.1),
    )

    score = 0.50
    for keyword, weight in keyword_buckets:
        if keyword in lowered:
            score += weight
    return min(0.95, max(0.50, round(score, 2)))


def _guess_product(text: str) -> ProductType:
    lowered = text.lower()
    if 'credit card' in lowered or 'card' in lowered:
        return ProductType.CREDIT_CARD
    if 'mortgage' in lowered:
        return ProductType.MORTGAGE
    if 'loan' in lowered:
        return ProductType.LOAN
    if 'bank account' in lowered or 'checking' in lowered or 'savings' in lowered:
        return ProductType.BANK_ACCOUNT
    if 'debt collection' in lowered or 'collector' in lowered:
        return ProductType.DEBT_COLLECTION
    if 'transfer' in lowered or 'wire' in lowered or 'zelle' in lowered:
        return ProductType.MONEY_TRANSFER
    return ProductType.OTHER


def _guess_issue(text: str) -> IssueType:
    lowered = text.lower()
    if 'fraud' in lowered or 'scam' in lowered:
        return IssueType.FRAUD
    if 'identity theft' in lowered or 'stolen identity' in lowered:
        return IssueType.IDENTITY_THEFT
    if 'billing' in lowered or 'charged' in lowered or 'fee' in lowered:
        return IssueType.BILLING
    if 'payment' in lowered or 'late' in lowered:
        return IssueType.PAYMENT
    if 'credit report' in lowered or 'credit bureau' in lowered:
        return IssueType.CREDIT_REPORTING
    if 'representative' in lowered or 'customer service' in lowered:
        return IssueType.CUSTOMER_SERVICE
    return IssueType.OTHER


def _guess_severity_and_risk(text: str) -> tuple[SeverityLevel, ComplianceRisk]:
    lowered = text.lower()
    critical_markers = ('lawsuit', 'identity theft', 'illegal', 'regulator', 'cfpb complaint')
    high_markers = ('fraud', 'unauthorized', 'harassment', 'foreclosure', 'eviction')

    if any(marker in lowered for marker in critical_markers):
        return SeverityLevel.CRITICAL, ComplianceRisk.HIGH
    if any(marker in lowered for marker in high_markers):
        return SeverityLevel.HIGH, ComplianceRisk.HIGH
    if 'billing' in lowered or 'payment' in lowered:
        return SeverityLevel.MEDIUM, ComplianceRisk.MEDIUM
    return SeverityLevel.LOW, ComplianceRisk.LOW


class ClassifierAgent:
    def __init__(
        self,
        *,
        llm_client: GroqLLMClient | None = None,
        transport: Any | None = None,
        repair_retries: int = SCHEMA_REPAIR_RETRIES,
    ) -> None:
        self._client = llm_client or GroqLLMClient(transport=transport)
        self.repair_retries = repair_retries
        self.last_llm_attempts = 0
        self.used_fallback = False

    def classify(self, payload: IntakePreparation | str) -> ClassificationResult:
        if isinstance(payload, str):
            complaint_text = payload
        else:
            complaint_text = payload.classifier_payload()['complaint_text']

        prompt = self._classification_prompt(complaint_text)
        self.last_llm_attempts = 0
        self.used_fallback = False

        raw_response = ''
        for attempt in range(self.repair_retries + 1):
            self.last_llm_attempts += 1
            response = self._client.complete(
                prompt=prompt,
                agent_name='classifier',
                critical=True,
                max_tokens=280,
            )
            raw_response = response.text
            parsed = self._parse_or_none(raw_response)
            if parsed is not None:
                return parsed
            if attempt < self.repair_retries:
                prompt = self._repair_prompt(complaint_text, raw_response)

        self.used_fallback = True
        return self._fallback_classification(complaint_text)

    def _parse_or_none(self, text: str) -> ClassificationResult | None:
        candidate = _extract_json_object(text)
        if candidate is None:
            return None

        try:
            return ClassificationResult.model_validate_json(candidate)
        except (ValidationError, json.JSONDecodeError):
            return None

    def _classification_prompt(self, complaint_text: str) -> str:
        return (
            'You are a complaint classifier. Return ONLY strict JSON with keys '
            'product_type, issue_type, severity, compliance_risk, confidence. '
            'Use constrained taxonomy values and include confidence [0,1].\n\n'
            f'Complaint:\n{complaint_text}'
        )

    def _repair_prompt(self, complaint_text: str, invalid_output: str) -> str:
        return (
            'Previous output failed schema validation. Return ONLY valid JSON with required keys:\n'
            'product_type, issue_type, severity, compliance_risk, confidence.\n'
            'No markdown, no explanation.\n\n'
            f'Complaint:\n{complaint_text}\n\n'
            f'Invalid output:\n{invalid_output}'
        )

    def _fallback_classification(self, complaint_text: str) -> ClassificationResult:
        product = _guess_product(complaint_text)
        issue = _guess_issue(complaint_text)
        severity, risk = _guess_severity_and_risk(complaint_text)
        confidence = keyword_score_confidence(complaint_text)
        return ClassificationResult(
            product_type=product,
            issue_type=issue,
            severity=severity,
            compliance_risk=risk,
            confidence=confidence,
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