"""Schemas for compliance audit verdicts on response drafts."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AuditVerdict(StrEnum):
    PASS = 'PASS'
    FAIL = 'FAIL'


class AuditReasonCode(StrEnum):
    MISSING_POLICY_CITATION = 'MISSING_POLICY_CITATION'
    UNSAFE_TONE = 'UNSAFE_TONE'
    OVERCOMMITMENT = 'OVERCOMMITMENT'
    STRUCTURE_MISSING = 'STRUCTURE_MISSING'
    UNCLEAR_RESOLUTION = 'UNCLEAR_RESOLUTION'


class ResponseAuditResult(BaseModel):
    model_config = ConfigDict(extra='forbid')

    verdict: AuditVerdict
    reason_codes: list[AuditReasonCode] = Field(default_factory=list)
    critique_summary: str = Field(min_length=1)
    must_fix_items: list[str] = Field(default_factory=list)
    rewrite_recommended: bool = False

    @model_validator(mode='after')
    def _validate_verdict_details(self) -> 'ResponseAuditResult':
        if self.verdict == AuditVerdict.FAIL and not self.reason_codes:
            raise ValueError('FAIL verdict must include at least one reason code')
        if self.verdict == AuditVerdict.PASS and self.must_fix_items:
            raise ValueError('PASS verdict cannot include must-fix items')
        return self
