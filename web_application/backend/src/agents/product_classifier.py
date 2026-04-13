"""Stage-1 classifier: identifies the financial product from a complaint.

Uses LLM structured output (JSON mode via response_format) so the model is
forced to return valid JSON. No regex extraction or keyword fallback.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from src.agents.prompts import (
    PRODUCT_CLASSIFIER_SYSTEM_PROMPT,
    build_product_classifier_prompt,
    build_product_repair_prompt,
)
from src.llm.client import GroqLLMClient
from src.schemas.classification import ProductClassificationResult, ProductType
from src.schemas.intake import IntakePreparation

SCHEMA_REPAIR_RETRIES = 2

_JSON_RESPONSE_FORMAT: dict[str, str] = {"type": "json_object"}


class ProductClassifierAgent:
    """LLM-backed stage-1 classifier using structured JSON output.

    Raises ValueError if schema validation fails after all repair retries.
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

    def classify_product(
        self, payload: IntakePreparation | str
    ) -> ProductClassificationResult:
        complaint_text = (
            payload
            if isinstance(payload, str)
            else payload.classifier_payload()["complaint_text"]
        )

        prompt = build_product_classifier_prompt(complaint_text)
        self.last_llm_attempts = 0
        self.used_fallback = False
        self.last_total_tokens = 0

        last_error: str = ""
        for attempt in range(self.repair_retries + 1):
            self.last_llm_attempts += 1
            response = self._client.complete(
                prompt=prompt,
                agent_name="product_classifier",
                system_prompt=PRODUCT_CLASSIFIER_SYSTEM_PROMPT,
                critical=True,
                max_tokens=160,
                response_format=_JSON_RESPONSE_FORMAT,
            )
            self.last_model = response.model
            self.last_total_tokens += response.total_tokens
            parsed, error = self._parse(response.text)
            if parsed is not None:
                return parsed
            last_error = error
            if attempt < self.repair_retries:
                prompt = build_product_repair_prompt(complaint_text, response.text, error)

        raise ValueError(
            f"ProductClassifier: schema validation failed after {self.repair_retries + 1} "
            f"attempts. Last error: {last_error}"
        )

    def _parse(self, text: str) -> tuple[ProductClassificationResult | None, str]:
        try:
            data = json.loads(text.strip())
            result = ProductClassificationResult.model_validate(data)
            return result, ""
        except json.JSONDecodeError as e:
            return None, f"JSONDecodeError: {e}"
        except ValidationError as e:
            return None, f"ValidationError: {e.errors()[0]['msg'] if e.errors() else str(e)}"
        except Exception as e:
            return None, str(e)
