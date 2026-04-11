"""Stage-2 classifier: identifies issue, severity, compliance risk (product-conditioned).

Uses LLM structured output (JSON mode). No keyword matching or regex fallback.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from src.agents.prompts import (
    ISSUE_CLASSIFIER_SYSTEM_PROMPT,
    build_issue_classifier_prompt,
    build_issue_repair_prompt,
)
from src.llm.client import GroqLLMClient
from src.schemas.classification import IssueClassificationResult, ProductType
from src.schemas.intake import IntakePreparation

SCHEMA_REPAIR_RETRIES = 2

_JSON_RESPONSE_FORMAT: dict[str, str] = {"type": "json_object"}


class IssueClassifierAgent:
    """LLM-backed stage-2 classifier using structured JSON output.

    Restricts the valid issue space to the product-specific CFPB taxonomy
    subset. Raises ValueError if schema validation fails after all repair retries.
    """

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
        self.last_model: str | None = None
        self.last_total_tokens = 0

    def classify_issue(
        self,
        payload: IntakePreparation | str,
        product: ProductType,
    ) -> IssueClassificationResult:
        complaint_text = (
            payload
            if isinstance(payload, str)
            else payload.classifier_payload()["complaint_text"]
        )

        prompt = build_issue_classifier_prompt(complaint_text, product)
        self.last_llm_attempts = 0
        self.used_fallback = False
        self.last_total_tokens = 0

        last_error: str = ""
        for attempt in range(self.repair_retries + 1):
            self.last_llm_attempts += 1
            response = self._client.complete(
                prompt=prompt,
                agent_name="issue_classifier",
                system_prompt=ISSUE_CLASSIFIER_SYSTEM_PROMPT,
                critical=True,
                max_tokens=200,
                response_format=_JSON_RESPONSE_FORMAT,
            )
            self.last_model = response.model
            self.last_total_tokens += response.total_tokens
            parsed, error = self._parse(response.text)
            if parsed is not None:
                return parsed
            last_error = error
            if attempt < self.repair_retries:
                prompt = build_issue_repair_prompt(complaint_text, product, response.text, error)

        raise ValueError(
            f"IssueClassifier: schema validation failed after {self.repair_retries + 1} "
            f"attempts. Last error: {last_error}"
        )

    def _parse(self, text: str) -> tuple[IssueClassificationResult | None, str]:
        try:
            data = json.loads(text.strip())
            result = IssueClassificationResult.model_validate(data)
            return result, ""
        except json.JSONDecodeError as e:
            return None, f"JSONDecodeError: {e}"
        except ValidationError as e:
            return None, f"ValidationError: {e.errors()[0]['msg'] if e.errors() else str(e)}"
        except Exception as e:
            return None, str(e)
