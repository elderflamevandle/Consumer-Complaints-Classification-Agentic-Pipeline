"""Two-stage complaint classifier: product → issue → combined ClassificationResult.

Orchestrates:
  1. ProductClassifierAgent  — LLM identifies the financial product
  2. IssueClassifierAgent    — LLM identifies the issue conditioned on product

No keyword matching or heuristic fallbacks. Both stages use LLM structured
output (JSON mode). Raises ValueError if either stage exhausts repair retries.
"""

from __future__ import annotations

from typing import Any

from src.agents.issue_classifier import IssueClassifierAgent
from src.agents.product_classifier import ProductClassifierAgent
from src.llm.client import GroqLLMClient
from src.schemas.classification import (
    ClassificationResult,
    IssueClassificationResult,
    ProductClassificationResult,
)
from src.schemas.intake import IntakePreparation

SCHEMA_REPAIR_RETRIES = 2


class ClassifierAgent:
    """Orchestrates two-stage LLM classification: product → issue.

    Exposes a single `.classify()` method returning ClassificationResult
    for full backward compatibility with the rest of the pipeline.

    Attributes:
        product_result: ProductClassificationResult from stage 1.
        issue_result:   IssueClassificationResult from stage 2.
        used_fallback:  Always False (no fallback; raises on failure instead).
    """

    def __init__(
        self,
        *,
        llm_client: GroqLLMClient | None = None,
        transport: Any | None = None,
        repair_retries: int = SCHEMA_REPAIR_RETRIES,
    ) -> None:
        self._client = llm_client or GroqLLMClient(transport=transport)
        self._product_classifier = ProductClassifierAgent(
            llm_client=self._client,
            repair_retries=repair_retries,
        )
        self._issue_classifier = IssueClassifierAgent(
            llm_client=self._client,
            repair_retries=repair_retries,
        )
        self.repair_retries = repair_retries
        self.product_result: ProductClassificationResult | None = None
        self.issue_result: IssueClassificationResult | None = None
        self.last_llm_attempts = 0
        self.used_fallback = False

    def classify(self, payload: IntakePreparation | str) -> ClassificationResult:
        """Run two-stage LLM classification and return merged ClassificationResult."""
        self.product_result = self._product_classifier.classify_product(payload)
        self.issue_result = self._issue_classifier.classify_issue(
            payload,
            self.product_result.product,
            product_reasoning=self.product_result.reasoning,
        )
        self.last_llm_attempts = (
            self._product_classifier.last_llm_attempts
            + self._issue_classifier.last_llm_attempts
        )
        return self.issue_result.to_classification_result(self.product_result.product)
