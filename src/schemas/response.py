"""Schemas for customer-facing response drafts."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _clean_text(value: str) -> str:
    return ' '.join(value.strip().split())


class InternalResponse(BaseModel):
    model_config = ConfigDict(extra='forbid')
    
    resolution_summary: str = Field(min_length=1)
    action_steps: list[str] = Field(min_length=1)

    @field_validator('resolution_summary', mode='before')
    @classmethod
    def _normalize_text_fields(cls, value: object) -> object:
        if isinstance(value, str):
            return _clean_text(value)
        return value

    @field_validator('action_steps', mode='before')
    @classmethod
    def _normalize_list_fields(cls, value: object) -> object:
        if isinstance(value, list):
            normalized: list[str] = []
            for item in value:
                if isinstance(item, str):
                    cleaned = _clean_text(item)
                    if cleaned:
                        normalized.append(cleaned)
            return normalized
        return value

class ExternalResponse(BaseModel):
    model_config = ConfigDict(extra='forbid')
    
    acknowledgment: str = Field(min_length=1)
    findings: str = Field(min_length=1)
    timeline: str = Field(min_length=1)

    @field_validator(
        'acknowledgment',
        'findings',
        'timeline',
        mode='before',
    )
    @classmethod
    def _normalize_text_fields(cls, value: object) -> object:
        if isinstance(value, str):
            return _clean_text(value)
        return value

class ResponseDraft(BaseModel):
    model_config = ConfigDict(extra='forbid')

    internal: InternalResponse
    external: ExternalResponse

    policy_citation_labels: list[str] = Field(default_factory=list)
    critique_items_addressed: list[str] = Field(default_factory=list)

    @field_validator(
        'policy_citation_labels',
        'critique_items_addressed',
        mode='before',
    )
    @classmethod
    def _normalize_list_fields(cls, value: object) -> object:
        if isinstance(value, list):
            normalized: list[str] = []
            for item in value:
                if isinstance(item, str):
                    cleaned = _clean_text(item)
                    if cleaned:
                        normalized.append(cleaned)
            return normalized
        return value

    def render_internal_view(self) -> str:
        action_lines = '\n'.join(
            f'{index}. {step}' for index, step in enumerate(self.internal.action_steps, start=1)
        )
        lines = [self.internal.resolution_summary]
        if self.policy_citation_labels:
            lines.append(f'Policy Labels: {"; ".join(self.policy_citation_labels)}')
        if self.critique_items_addressed:
            lines.append(f'Addressed Critiques: {"; ".join(self.critique_items_addressed)}')
            
        summary_block = '\n'.join(lines)
        return (
            'Internal Summary:\n'
            f'{summary_block}\n\n'
            'Action Steps:\n'
            f'{action_lines}'
        )

    def render_external_response(self) -> str:
        return (
            'Acknowledgment:\n'
            f'{self.external.acknowledgment}\n\n'
            'Findings:\n'
            f'{self.external.findings}\n\n'
            'Timeline:\n'
            f'{self.external.timeline}'
        )
