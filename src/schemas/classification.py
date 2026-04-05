"""Classification schema contracts used by classifier output parsing."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ClassificationResult(BaseModel):
    product_type: str = Field(min_length=1)
    issue_type: str = Field(min_length=1)
    severity: Literal['low', 'medium', 'high', 'critical']
    compliance_risk: Literal['low', 'medium', 'high']
    confidence: float = Field(ge=0.0, le=1.0)