"""Schemas for customer-facing response drafts."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _clean_text(value: str) -> str:
    return ' '.join(value.strip().split())


class ResponseDraft(BaseModel):
    model_config = ConfigDict(extra='forbid')

    resolution_statement: str = Field(min_length=1)
    acknowledgment: str = Field(min_length=1)
    findings: str = Field(min_length=1)
    action_steps: list[str] = Field(min_length=1)
    timeline_next_steps: str = Field(min_length=1)
    policy_citation_labels: list[str] = Field(default_factory=list)
    critique_items_addressed: list[str] = Field(default_factory=list)

    @field_validator(
        'resolution_statement',
        'acknowledgment',
        'findings',
        'timeline_next_steps',
        mode='before',
    )
    @classmethod
    def _normalize_text_fields(cls, value: object) -> object:
        if isinstance(value, str):
            return _clean_text(value)
        return value

    @field_validator(
        'action_steps',
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

    def render_text(self) -> str:
        action_lines = '\n'.join(
            f'{index}. {step}' for index, step in enumerate(self.action_steps, start=1)
        )
        findings_lines = [self.resolution_statement, self.findings]
        if self.policy_citation_labels:
            findings_lines.append(
                f'Policy Labels: {"; ".join(self.policy_citation_labels)}'
            )
        if self.critique_items_addressed:
            findings_lines.append(
                f'Addressed Critiques: {"; ".join(self.critique_items_addressed)}'
            )
        findings_block = '\n'.join(findings_lines)
        return (
            'Acknowledgment:\n'
            f'{self.acknowledgment}\n\n'
            'Findings:\n'
            f'{findings_block}\n\n'
            'Action Steps:\n'
            f'{action_lines}\n\n'
            'Timeline / Next Steps:\n'
            f'{self.timeline_next_steps}'
        )
