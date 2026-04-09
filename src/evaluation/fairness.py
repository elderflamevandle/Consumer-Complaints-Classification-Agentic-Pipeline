"""Fairness reporting for selected complaint product groups."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from src.evaluation.harness import EvaluationRow
from src.evaluation.taxonomy import _clean_label

FAIRNESS_GROUP_ORDER = (
    'CREDIT_REPORTING',
    'DEBT_COLLECTION',
    'BANK_ACCOUNT',
    'MORTGAGE',
    'MONEY_TRANSFER',
    'CREDIT_CARD',
    'LOAN',
)
DEFAULT_BASELINE_GROUP = 'CREDIT_REPORTING'
DEFAULT_MIN_SUPPORT = 50

_PRODUCT_GROUP_ALIASES = {
    'bank account or service': 'BANK_ACCOUNT',
    'checking or savings account': 'BANK_ACCOUNT',
    'consumer loan': 'LOAN',
    'credit card': 'CREDIT_CARD',
    'credit card or prepaid card': 'CREDIT_CARD',
    'credit reporting': 'CREDIT_REPORTING',
    'credit reporting or other personal consumer reports': 'CREDIT_REPORTING',
    (
        'credit reporting credit repair services or other personal consumer reports'
    ): 'CREDIT_REPORTING',
    'debt collection': 'DEBT_COLLECTION',
    'money transfer virtual currency or money service': 'MONEY_TRANSFER',
    'mortgage': 'MORTGAGE',
    'payday loan title loan or personal loan': 'LOAN',
    'payday loan title loan personal loan or advance loan': 'LOAN',
    'prepaid card': 'CREDIT_CARD',
    'student loan': 'LOAN',
    'vehicle loan or lease': 'LOAN',
}


@dataclass(frozen=True)
class FairnessComparison:
    group: str
    support: int
    exact_match_rate: float
    baseline_group: str
    baseline_support: int
    baseline_exact_match_rate: float
    disparity_ratio: float


@dataclass(frozen=True)
class SkippedGroup:
    group: str
    support: int
    reason: str


@dataclass(frozen=True)
class FairnessReport:
    baseline_group: str
    baseline_support: int
    baseline_exact_match_rate: float
    min_support: int
    selected_groups: tuple[str, ...]
    comparisons: tuple[FairnessComparison, ...]
    skipped_groups: tuple[SkippedGroup, ...]
    warnings: tuple[str, ...]



def canonicalize_product_group(raw_product: str) -> str:
    return _PRODUCT_GROUP_ALIASES.get(_clean_label(raw_product), 'OTHER')



def build_fairness_report(
    rows: Sequence[EvaluationRow],
    *,
    baseline_group: str = DEFAULT_BASELINE_GROUP,
    min_support: int = DEFAULT_MIN_SUPPORT,
    selected_groups: Sequence[str] = FAIRNESS_GROUP_ORDER,
) -> FairnessReport:
    grouped: dict[str, list[EvaluationRow]] = {}
    for row in rows:
        group = canonicalize_product_group(row.raw_product)
        grouped.setdefault(group, []).append(row)

    baseline_rows = grouped.get(baseline_group, [])
    baseline_support = len(baseline_rows)
    baseline_exact_match_rate = _round(_exact_match_rate(baseline_rows))
    warnings: list[str] = []

    if baseline_support < min_support:
        warning = (
            f'Baseline {baseline_group} skipped: support {baseline_support} < min_support '
            f'{min_support}.'
        )
        warnings.append(warning)
        return FairnessReport(
            baseline_group=baseline_group,
            baseline_support=baseline_support,
            baseline_exact_match_rate=baseline_exact_match_rate,
            min_support=min_support,
            selected_groups=tuple(selected_groups),
            comparisons=(),
            skipped_groups=(),
            warnings=tuple(warnings),
        )

    comparisons: list[FairnessComparison] = []
    skipped_groups: list[SkippedGroup] = []
    for group in selected_groups:
        if group == baseline_group:
            continue

        group_rows = grouped.get(group, [])
        support = len(group_rows)
        if support == 0:
            continue
        if support < min_support:
            reason = f'support {support} < min_support {min_support}'
            skipped_groups.append(SkippedGroup(group=group, support=support, reason=reason))
            warnings.append(f'Skipped {group}: {reason}.')
            continue

        exact_match_rate = _round(_exact_match_rate(group_rows))
        disparity_ratio = 0.0
        if baseline_exact_match_rate > 0.0:
            disparity_ratio = _round(exact_match_rate / baseline_exact_match_rate)
        comparisons.append(
            FairnessComparison(
                group=group,
                support=support,
                exact_match_rate=exact_match_rate,
                baseline_group=baseline_group,
                baseline_support=baseline_support,
                baseline_exact_match_rate=baseline_exact_match_rate,
                disparity_ratio=disparity_ratio,
            )
        )

    return FairnessReport(
        baseline_group=baseline_group,
        baseline_support=baseline_support,
        baseline_exact_match_rate=baseline_exact_match_rate,
        min_support=min_support,
        selected_groups=tuple(selected_groups),
        comparisons=tuple(comparisons),
        skipped_groups=tuple(skipped_groups),
        warnings=tuple(warnings),
    )



def _exact_match_rate(rows: Sequence[EvaluationRow]) -> float:
    if not rows:
        return 0.0
    return sum(1 for row in rows if row.exact_match) / len(rows)



def _round(value: float) -> float:
    return round(value, 4)

