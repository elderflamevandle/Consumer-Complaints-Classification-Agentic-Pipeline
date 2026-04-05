"""Root-cause diagnosis agent using retrieved similar complaints as evidence."""

from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Callable
from typing import Any

from pydantic import ValidationError

from src.llm.client import GroqLLMClient
from src.schemas.root_cause import (
    AmbiguityFlag,
    EvidenceCitation,
    RootCauseEvidence,
    RootCauseResult,
)
from src.tools.vector_search import RetrievedCase, retrieve_similar_cases

SCHEMA_REPAIR_RETRIES = 1


class RootCauseAgent:
    def __init__(
        self,
        *,
        llm_client: GroqLLMClient | None = None,
        transport: Any | None = None,
        retriever: Callable[..., list[RetrievedCase]] | None = None,
        repair_retries: int = SCHEMA_REPAIR_RETRIES,
    ) -> None:
        self._client = llm_client or GroqLLMClient(transport=transport)
        self._retriever = retriever or retrieve_similar_cases
        self.repair_retries = repair_retries
        self.last_llm_attempts = 0
        self.used_fallback = False

    def diagnose(
        self,
        complaint_text: str,
        *,
        limit: int = 5,
    ) -> RootCauseResult:
        cases = self._retriever(query_text=complaint_text, limit=limit)
        self.last_llm_attempts = 0
        self.used_fallback = False

        prompt = self._prompt(complaint_text, cases)
        raw_output = ''
        for attempt in range(self.repair_retries + 1):
            self.last_llm_attempts += 1
            response = self._client.complete(
                prompt=prompt,
                agent_name='root_cause',
                critical=True,
                max_tokens=420,
            )
            raw_output = response.text
            parsed = self._parse_or_none(raw_output)
            if parsed is not None:
                return parsed
            if attempt < self.repair_retries:
                prompt = self._repair_prompt(complaint_text, cases, raw_output)

        self.used_fallback = True
        return self._fallback_result(cases)

    def _parse_or_none(self, text: str) -> RootCauseResult | None:
        candidate = _extract_json_object(text)
        if candidate is None:
            return None
        try:
            parsed = RootCauseResult.model_validate_json(candidate)
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
        lines: list[str] = []
        for idx, case in enumerate(cases, start=1):
            lines.append(
                (
                    f'{idx}. id={case.id} product={case.product} issue={case.issue} '
                    f'date={case.date} score={case.score:.4f}\n'
                    f'   narrative={case.narrative[:260]}'
                )
            )

        retrieved_block = '\n'.join(lines) if lines else 'No retrieved evidence available.'
        return (
            'You are the root-cause analyst for complaint resolution.\n'
            'Return ONLY valid JSON with keys:\n'
            'root_cause (string), evidence (array max 5), ambiguity_flag (CLEAR|AMBIGUOUS).\n'
            'Each evidence item must include: rank, summary, score, '
            'citation{id,product,issue,date}.\n\n'
            f'Complaint:\n{complaint_text}\n\n'
            f'Retrieved similar complaints:\n{retrieved_block}'
        )

    def _repair_prompt(
        self,
        complaint_text: str,
        cases: list[RetrievedCase],
        invalid_output: str,
    ) -> str:
        return (
            'Previous output failed schema validation. Return ONLY valid JSON with keys:\n'
            'root_cause, evidence, ambiguity_flag.\n'
            'evidence items need: rank, summary, score, citation{id,product,issue,date}.\n'
            'No markdown, no explanations.\n\n'
            f'{self._prompt(complaint_text, cases)}\n\n'
            f'Invalid output:\n{invalid_output}'
        )

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


def _extract_json_object(text: str) -> str | None:
    stripped = text.strip()
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
