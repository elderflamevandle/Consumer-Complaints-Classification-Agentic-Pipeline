"""Root-cause diagnosis agent using retrieved similar complaints as evidence."""

from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Callable
from typing import Any

from pydantic import ValidationError

from src.agents.prompts import build_root_cause_prompt, build_root_cause_repair_prompt
from src.agents.prompts import build_root_cause_prompt, build_root_cause_repair_prompt
from src.llm.client import GroqLLMClient
from src.schemas.root_cause import (
    AmbiguityFlag,
    EvidenceCitation,
    RootCauseEvidence,
    RootCauseResult,
)
from src.tools.audit_logger import AuditLogger
from src.tools.vector_search import RetrievedCase, retrieve_similar_cases

SCHEMA_REPAIR_RETRIES = 1
_JSON_RESPONSE_FORMAT: dict[str, str] = {"type": "json_object"}


class RootCauseAgent:
    def __init__(
        self,
        *,
        llm_client: GroqLLMClient | None = None,
        transport: Any | None = None,
        retriever: Callable[..., list[RetrievedCase]] | None = None,
        repair_retries: int = SCHEMA_REPAIR_RETRIES,
        audit_logger: AuditLogger | None = None,
    ) -> None:
        self._client = llm_client or GroqLLMClient(transport=transport)
        self._retriever = retriever or retrieve_similar_cases
        self.repair_retries = repair_retries
        self._audit_logger = audit_logger
        self.last_llm_attempts = 0
        self.last_model: str | None = None
        self.used_fallback = False
        self.last_total_tokens = 0

    def diagnose(
        self,
        complaint_text: str,
        *,
        limit: int = 5,
        thread_id: str | None = None,
    ) -> RootCauseResult:
        cases = self._retriever(query_text=complaint_text, limit=limit)
        self.last_llm_attempts = 0
        self.last_model = None
        self.used_fallback = False
        self.last_total_tokens = 0

        prompt = self._prompt(complaint_text, cases)
        raw_output = ''
        for attempt in range(self.repair_retries + 1):
            self.last_llm_attempts += 1
            response = self._client.complete(
                prompt=prompt,
                agent_name='root_cause',
                critical=True,
                max_tokens=1000,
                response_format=_JSON_RESPONSE_FORMAT,
            )
            self.last_model = response.model
            self.last_total_tokens += response.total_tokens
            raw_output = response.text
            parsed = self._parse_or_none(raw_output)
            if parsed is not None:
                self._log_outcome(
                    thread_id=thread_id,
                    model=response.model,
                    decision=f'diagnosis_{parsed.ambiguity_flag.value.lower()}',
                    scrubbed_text=complaint_text,
                )
                return parsed
            if attempt < self.repair_retries:
                prompt = self._repair_prompt(complaint_text, cases, raw_output)

        self.used_fallback = True
        self.last_model = 'heuristic-fallback'
        fallback = self._fallback_result(cases)
        self._log_outcome(
            thread_id=thread_id,
            model='heuristic-fallback',
            decision=f'diagnosis_{fallback.ambiguity_flag.value.lower()}',
            scrubbed_text=complaint_text,
        )
        return fallback

    def _parse_or_none(self, text: str) -> RootCauseResult | None:
        candidate = _extract_json_object(text)
        if candidate is None:
            return None
        try:
            data = json.loads(candidate)
            # Use model_validate (not model_validate_json) so Pydantic's lax
            # coercion runs — e.g. LLM may return citation id as int, not str.
            parsed = RootCauseResult.model_validate(data)
        except (ValidationError, json.JSONDecodeError):
            return None

        ordered = sorted(parsed.evidence, key=lambda item: item.rank)[:5]
        normalized_evidence: list[RootCauseEvidence] = []
        for index, item in enumerate(ordered, start=1):
            normalized_evidence.append(
                RootCauseEvidence(
                    rank=index,
                    summary=item.summary,
                    citation=item.citation,
                    score=item.score,
                )
            )

        return RootCauseResult(
            root_cause=parsed.root_cause,
            evidence=normalized_evidence,
            ambiguity_flag=parsed.ambiguity_flag,
        )

    def _prompt(self, complaint_text: str, cases: list[RetrievedCase]) -> str:
        return build_root_cause_prompt(complaint_text, cases)

    def _repair_prompt(
        self,
        complaint_text: str,
        cases: list[RetrievedCase],
        invalid_output: str,
    ) -> str:
        return build_root_cause_repair_prompt(complaint_text, cases, invalid_output)

    def _fallback_result(self, cases: list[RetrievedCase]) -> RootCauseResult:
        if not cases:
            return RootCauseResult(
                root_cause='Insufficient retrieved evidence to determine a primary root cause.',
                evidence=[
                    RootCauseEvidence(
                        rank=1,
                        summary='No similar historical complaints were retrieved for comparison.',
                        citation=EvidenceCitation(
                            id='N/A',
                            product='UNKNOWN',
                            issue='UNKNOWN',
                            date='N/A',
                        ),
                        score=0.0,
                    )
                ],
                ambiguity_flag=AmbiguityFlag.AMBIGUOUS,
            )

        issue_counts = Counter(case.issue for case in cases)
        top_issue, top_count = issue_counts.most_common(1)[0]
        ambiguous = top_count <= (len(cases) / 2.0)

        if ambiguous:
            root_cause = (
                'AMBIGUOUS evidence profile: no single issue dominates retrieved complaints.'
            )
            flag = AmbiguityFlag.AMBIGUOUS
        else:
            root_cause = (
                f'Majority retrieved evidence points to recurring "{top_issue}" failure pattern.'
            )
            flag = AmbiguityFlag.CLEAR

        evidence: list[RootCauseEvidence] = []
        for idx, case in enumerate(cases[:5], start=1):
            evidence.append(
                RootCauseEvidence(
                    rank=idx,
                    summary=case.narrative[:180],
                    citation=EvidenceCitation(
                        id=case.id,
                        product=case.product,
                        issue=case.issue,
                        date=case.date,
                    ),
                    score=case.score,
                )
            )

        return RootCauseResult(
            root_cause=root_cause,
            evidence=evidence,
            ambiguity_flag=flag,
        )

    def _log_outcome(
        self,
        *,
        thread_id: str | None,
        model: str,
        decision: str,
        scrubbed_text: str,
    ) -> None:
        if thread_id is None or self._audit_logger is None:
            return
        self._audit_logger.log_node_outcome(
            thread_id=thread_id,
            node='root_cause',
            model=model,
            latency_ms=0,
            decision=decision,
            scrubbed_text=scrubbed_text[:220],
        )


def _extract_json_object(text: str) -> str | None:
    # Strip complete <think>...</think> blocks (reasoning models like DeepSeek/Qwen).
    stripped = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()

    # If <think> was truncated (no closing tag), discard everything before it —
    # the actual JSON always appears after the thinking block.
    if '<think>' in stripped:
        stripped = stripped[stripped.index('<think>'):].split('<think>', 1)[-1]
        # At this point we have the raw tail after <think> with no </think>.
        # The JSON, if present, is at the very end — find the last '{'.
        last_brace = stripped.rfind('{')
        if last_brace != -1:
            stripped = stripped[last_brace:]
        else:
            return None

    stripped = stripped.strip()
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
