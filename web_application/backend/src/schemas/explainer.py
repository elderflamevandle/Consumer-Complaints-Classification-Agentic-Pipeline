"""Schemas for final stage-chain explanations."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ExplanationBullet(BaseModel):
    model_config = ConfigDict(extra='forbid')

    stage: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    citations: list[str] = Field(default_factory=list)


class ExplanationResult(BaseModel):
    model_config = ConfigDict(extra='forbid')

    bullets: list[ExplanationBullet] = Field(min_length=5, max_length=7)

    def render_text(self) -> str:
        lines: list[str] = []
        for bullet in self.bullets:
            citation_suffix = ''
            if bullet.citations:
                citation_suffix = f' ({", ".join(bullet.citations)})'
            lines.append(f'- [{bullet.stage}] {bullet.summary}{citation_suffix}')
        return '\n'.join(lines)
