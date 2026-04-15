"""Schemas for retrieval-grounded root-cause diagnosis outputs."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AmbiguityFlag(StrEnum):
    CLEAR = 'CLEAR'
    AMBIGUOUS = 'AMBIGUOUS'


class EvidenceCitation(BaseModel):
    model_config = ConfigDict(extra='forbid')

    id: str
    product: str
    issue: str
    date: str

    @field_validator('id', mode='before')
    @classmethod
    def coerce_id_to_str(cls, v: object) -> str:
        return str(v)


class RootCauseEvidence(BaseModel):
    model_config = ConfigDict(extra='forbid')

    rank: int = Field(ge=1, le=5)
    summary: str = Field(min_length=1)
    citation: EvidenceCitation
    score: float = Field(ge=0.0)


class RootCauseResult(BaseModel):
    model_config = ConfigDict(extra='forbid')

    root_cause: str = Field(min_length=1)
    evidence: list[RootCauseEvidence] = Field(min_length=1, max_length=5)
    ambiguity_flag: AmbiguityFlag = AmbiguityFlag.CLEAR

