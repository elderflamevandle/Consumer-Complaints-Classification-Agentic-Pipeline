from __future__ import annotations

from typing import Any

from src.agents.root_cause import RootCauseAgent
from src.schemas.root_cause import AmbiguityFlag
from src.tools.vector_search import RetrievedCase, retrieve_similar_cases


class ScriptedTransport:
    def __init__(self, outputs: list[Any]) -> None:
        self.outputs = outputs
        self.calls = 0

    def __call__(self, **_: Any) -> dict[str, Any]:
        self.calls += 1
        if not self.outputs:
            return {'content': '{}', 'usage': {'total_tokens': 16}}

        output = self.outputs.pop(0)
        if isinstance(output, Exception):
            raise output
        return {'content': output, 'usage': {'total_tokens': 16}}


def _record(
    *,
    case_id: str,
    product: str,
    issue: str,
    date: str,
    narrative: str,
) -> dict[str, Any]:
    return {
        'id': case_id,
        'text': narrative,
        'metadata': {
            'id': case_id,
            'product': product,
            'issue': issue,
            'date': date,
            'state': 'CA',
        },
    }


def _case(
    *,
    case_id: str,
    product: str = 'credit_card',
    issue: str = 'billing',
    date: str = '2025-01-01',
    narrative: str = 'narrative',
    score: float = 0.5,
) -> RetrievedCase:
    return RetrievedCase(
        id=case_id,
        product=product,
        issue=issue,
        date=date,
        state='CA',
        narrative=narrative,
        score=score,
    )


def test_retrieves_top5_similar_cases() -> None:
    records = [
        _record(
            case_id='001',
            product='credit_card',
            issue='fraud',
            date='2025-01-01',
            narrative='Unauthorized credit card charge and fraud alert was ignored',
        ),
        _record(
            case_id='002',
            product='credit_card',
            issue='billing',
            date='2025-01-02',
            narrative='Billing dispute after duplicate card charge on account',
        ),
        _record(
            case_id='003',
            product='mortgage',
            issue='payment',
            date='2025-01-03',
            narrative='Mortgage payment posting delay with late fee',
        ),
        _record(
            case_id='004',
            product='bank_account',
            issue='fraud',
            date='2025-01-04',
            narrative='Unauthorized transfer from checking account and fraud report',
        ),
        _record(
            case_id='005',
            product='credit_card',
            issue='customer_service',
            date='2025-01-05',
            narrative='Credit card support repeatedly dropped dispute calls',
        ),
        _record(
            case_id='006',
            product='loan',
            issue='billing',
            date='2025-01-06',
            narrative='Loan statement has unexpected billing fees and penalties',
        ),
        _record(
            case_id='007',
            product='debt_collection',
            issue='harassment',
            date='2025-01-07',
            narrative='Collector called repeatedly with aggressive threats',
        ),
    ]

    result = retrieve_similar_cases(
        query_text='unauthorized credit card fraud charge',
        limit=5,
        records=records,
    )

    assert len(result) == 5
    assert result[0].id in {'001', '004'}
    scores = [case.score for case in result]
    assert scores == sorted(scores, reverse=True)


def test_root_cause_outputs_ranked_evidence_with_citations() -> None:
    transport = ScriptedTransport(
        [
            (
                '{"root_cause":"Recurring dispute handling failure",'
                '"ambiguity_flag":"CLEAR",'
                '"evidence":['
                '{"rank":1,"summary":"Prior dispute ignored","score":0.88,'
                '"citation":{"id":"101","product":"credit_card","issue":"billing","date":"2025-01-10"}},'
                '{"rank":2,"summary":"Unauthorized charge repeat","score":0.81,'
                '"citation":{"id":"102","product":"credit_card","issue":"fraud","date":"2025-01-11"}}'
                ']}'
            )
        ]
    )
    cases = [
        _case(case_id='101', issue='billing', narrative='prior dispute ignored', score=0.88),
        _case(case_id='102', issue='fraud', narrative='unauthorized repeat', score=0.81),
    ]

    agent = RootCauseAgent(
        transport=transport,
        retriever=lambda **_: cases,
    )
    result = agent.diagnose('Card dispute keeps repeating')

    assert result.root_cause
    assert result.ambiguity_flag == AmbiguityFlag.CLEAR
    assert len(result.evidence) == 2
    assert [item.rank for item in result.evidence] == [1, 2]
    assert result.evidence[0].citation.id == '101'
    assert result.evidence[1].citation.product == 'credit_card'
    assert agent.last_model is not None
    assert agent.used_fallback is False


def test_conflicting_evidence_sets_ambiguous_flag() -> None:
    transport = ScriptedTransport(['not-json', 'still-not-json'])
    conflicting_cases = [
        _case(case_id='201', issue='billing', narrative='billing mismatch', score=0.7),
        _case(case_id='202', issue='fraud', narrative='fraud complaint', score=0.68),
        _case(case_id='203', issue='payment', narrative='payment not posted', score=0.67),
        _case(case_id='204', issue='credit_reporting', narrative='reporting issue', score=0.66),
        _case(case_id='205', issue='customer_service', narrative='service escalation', score=0.65),
    ]

    agent = RootCauseAgent(
        transport=transport,
        retriever=lambda **_: conflicting_cases,
        repair_retries=1,
    )
    result = agent.diagnose('Multiple complaint patterns with no dominant trend')

    assert transport.calls == 2
    assert agent.last_model == 'heuristic-fallback'
    assert agent.used_fallback is True
    assert result.ambiguity_flag == AmbiguityFlag.AMBIGUOUS
    assert len(result.evidence) == 5
    assert result.evidence[0].citation.id == '201'

