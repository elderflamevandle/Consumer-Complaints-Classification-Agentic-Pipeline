"""Run product+issue classification on demo CSV rows and print actual vs predicted issues."""

from __future__ import annotations

import csv
from argparse import ArgumentParser
from pathlib import Path

from src.agents.issue_classifier import IssueClassifierAgent
from src.agents.product_classifier import ProductClassifierAgent
from src.intake.pipeline import prepare_intake

DEFAULT_INPUT = Path('data/demos_10.csv')


def main() -> int:
    parser = ArgumentParser(
        description='Compare actual vs predicted issue labels on a demo CSV.'
    )
    parser.add_argument('--input', default=str(DEFAULT_INPUT))
    parser.add_argument('--limit', type=int, default=10)
    args = parser.parse_args()

    input_path = Path(args.input)
    rows = list(csv.DictReader(input_path.open('r', encoding='utf-8', newline='')))
    rows = rows[: max(args.limit, 0)]

    product_agent = ProductClassifierAgent()
    issue_agent = IssueClassifierAgent()

    print('id,actual_issue,predicted_issue')
    for row in rows:
        intake = prepare_intake(raw_text=row['narrative'])
        product_result = product_agent.classify_product(intake)
        issue_result = issue_agent.classify_issue(
            intake,
            product_result.product,
            product_reasoning=product_result.reasoning,
        )
        actual_issue = row['issue'].replace(',', ';')
        predicted_issue = issue_result.issue.value.replace(',', ';')
        print(f"{row['id']},{actual_issue},{predicted_issue}")

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
