"""Resumable batch evaluation for the full complaint pipeline on holdout data.

This script evaluates the real LangGraph pipeline on `holdout.parquet` and
persists row-level outputs so interrupted runs can resume without recomputing
completed complaints.

Default strategy:
  - Evaluate the first 60 rows only
  - Process sequentially in batches of 10
  - Save every completed row to JSONL
  - Refresh summary metrics after each batch

Metrics:
  - Product classification: accuracy, precision, recall, F1
  - Issue classification: accuracy, precision, recall, F1
  - Joint exact-match accuracy across product + issue
  - Root-cause quality: ROUGE-L vs complaint, evidence count, clear-rate
  - Final response quality: ROUGE-L vs grounded reference bundle, audit pass-rate
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import statistics
import sys
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from src.graph.pipeline import build_graph, run_complaint
from src.schemas.taxonomy import ALL_ISSUES, PRODUCT_DISPLAY_NAMES, PRODUCT_ISSUE_HIERARCHY

DEFAULT_DATASET_PATH = Path("data/processed/holdout.parquet")
DEFAULT_OUTPUT_DIR = Path("performance/artifacts")
DEFAULT_LIMIT = 60
DEFAULT_BATCH_SIZE = 10


PRODUCT_ALIASES: dict[str, str] = {
    "bank account or service": "CHECKING_SAVINGS_ACCOUNT",
    "checking or savings account": "CHECKING_SAVINGS_ACCOUNT",
    "consumer loan": "VEHICLE_LOAN_LEASE",
    "credit card": "CREDIT_CARD",
    "credit card or prepaid card": "CREDIT_CARD",
    "credit reporting": "CREDIT_REPORTING",
    "credit reporting or other personal consumer reports": "CREDIT_REPORTING",
    "credit reporting credit repair services or other personal consumer reports": "CREDIT_REPORTING",
    "debt collection": "DEBT_COLLECTION",
    "money transfer virtual currency or money service": "MONEY_TRANSFER",
    "mortgage": "MORTGAGE",
    "payday loan title loan or personal loan": "VEHICLE_LOAN_LEASE",
    "payday loan title loan personal loan or advance loan": "VEHICLE_LOAN_LEASE",
    "prepaid card": "CREDIT_CARD",
    "student loan": "VEHICLE_LOAN_LEASE",
    "vehicle loan or lease": "VEHICLE_LOAN_LEASE",
}

ISSUE_ALIASES: dict[str, str] = {
    "credit monitoring or identity theft protection services": "Credit monitoring or identity theft protection services",
    "incorrect information on credit report": "Incorrect information on your report",
    "incorrect information on your report": "Incorrect information on your report",
    "improper use of your report": "Improper use of your report",
    "problem with a company s investigation into an existing problem": "Problem with a company's investigation into an existing problem",
    "problem with a credit reporting company s investigation into an existing problem": "Problem with a company's investigation into an existing problem",
    "problem with fraud alerts or security freezes": "Problem with fraud alerts or security freezes",
    "problem with personal statement of dispute": "Problem with a company's investigation into an existing issue",
    "unable to get your credit report or credit score": "Unable to get your credit report or credit score",
    "identity theft protection or other monitoring services": "Identity theft protection or other monitoring services",
    "loan modification collection foreclosure": "Struggling to pay mortgage",
    "loan servicing payments escrow account": "Trouble during payment process",
    "money was not available when promised": "Money was not available when promised",
    "problem caused by your funds being low": "Problem caused by your funds being low",
    "problem when making payments": "Problem when making payments",
    "struggling to pay mortgage": "Struggling to pay mortgage",
    "struggling to repay your loan": "Struggling to pay your loan",
    "trouble during payment process": "Trouble during payment process",
    "fees or interest": "Fees or interest",
    "other transaction problem": "Other transaction problem",
    "problem with a lender or other company charging your account": "Problem with a lender or other company charging your account",
    "problem with a purchase or transfer": "Problem with a purchase shown on your statement",
    "problem with a purchase shown on your statement": "Problem with a purchase shown on your statement",
    "fraud or scam": "Fraud or scam",
    "unauthorized transactions or other transaction problem": "Unauthorized transactions or other transaction problem",
    "account opening closing or management": "Managing an account",
    "applying for a mortgage or refinancing an existing mortgage": "Applying for a mortgage or refinancing an existing mortgage",
    "closing an account": "Closing an account",
    "closing cancelling account": "Closing your account",
    "closing on a mortgage": "Closing on a mortgage",
    "closing your account": "Closing your account",
    "dealing with my lender or servicer": "Struggling to pay mortgage",
    "dealing with your lender or servicer": "Struggling to pay mortgage",
    "electronic communications": "Electronic communications",
    "getting a credit card": "Getting a credit card",
    "managing an account": "Managing an account",
    "managing opening or closing account": "Managing an account",
    "managing opening or closing your mobile wallet account": "Managing, opening, or closing your mobile wallet account",
    "managing the loan or lease": "Managing the loan or lease",
    "opening an account": "Opening an account",
    "other features terms or problems": "Other features, terms, or problems",
    "problem with customer service": "Problem with customer service",
    "trouble using the card": "Trouble using your card",
    "attempts to collect debt not owed": "Attempts to collect debt not owed",
    "communication tactics": "Communication tactics",
    "cont d attempts collect debt not owed": "Attempts to collect debt not owed",
    "false statements or representation": "False statements or representation",
    "took or threatened to take negative or legal action": "Took or threatened to take negative or legal action",
    "written notification about debt": "Written notification about debt",
}

EXACT_ISSUE_LOOKUP = {" ".join(issue.lower().split()): issue for issue in ALL_ISSUES}
PRODUCT_LABELS = list(PRODUCT_ISSUE_HIERARCHY.keys())
ISSUE_LABELS = list(ALL_ISSUES)


@dataclass(frozen=True)
class HoldoutRecord:
    complaint_id: str
    complaint_text: str
    state_code: str
    date: str
    raw_product: str
    raw_issue: str
    truth_product: str
    truth_issue: str


def _clean_label(value: str) -> str:
    return " ".join("".join(ch.lower() if ch.isalnum() else " " for ch in value).split())


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    _ensure_parent(path)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True, default=_json_default))
        handle.write("\n")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    _ensure_parent(path)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=_json_default), encoding="utf-8")


def _setup_logging(log_path: Path) -> logging.Logger:
    _ensure_parent(log_path)
    logger = logging.getLogger("performance.evaluate_holdout")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    return logger


def _normalize_truth_product(raw_product: str) -> str:
    product_token = _clean_label(raw_product)
    mapped = PRODUCT_ALIASES.get(product_token)
    if mapped:
        return mapped
    squashed = product_token.replace(" ", "_").upper()
    if squashed in PRODUCT_ISSUE_HIERARCHY:
        return squashed
    if "credit report" in product_token:
        return "CREDIT_REPORTING"
    if "debt" in product_token:
        return "DEBT_COLLECTION"
    if "mortgage" in product_token:
        return "MORTGAGE"
    if "money transfer" in product_token or "wallet" in product_token:
        return "MONEY_TRANSFER"
    if "card" in product_token:
        return "CREDIT_CARD"
    if "account" in product_token:
        return "CHECKING_SAVINGS_ACCOUNT"
    if "loan" in product_token or "lease" in product_token:
        return "VEHICLE_LOAN_LEASE"
    raise ValueError(f"Unsupported product label: {raw_product!r}")


def _normalize_truth_issue(raw_product: str, raw_issue: str) -> str:
    issue_token = _clean_label(raw_issue)
    exact = EXACT_ISSUE_LOOKUP.get(" ".join(raw_issue.lower().split()))
    if exact:
        return exact

    alias = ISSUE_ALIASES.get(issue_token)
    if alias:
        return alias

    product_key = _normalize_truth_product(raw_product)
    valid_issues = PRODUCT_ISSUE_HIERARCHY.get(product_key, [])
    valid_lookup = {_clean_label(issue): issue for issue in valid_issues}
    if issue_token in valid_lookup:
        return valid_lookup[issue_token]

    if "fraud" in issue_token or "unauthorized" in issue_token:
        for candidate in valid_issues:
            if candidate in {
                "Fraud or scam",
                "Unauthorized transactions or other transaction problem",
                "Identity theft protection or other monitoring services",
            }:
                return candidate

    if "payment" in issue_token or "escrow" in issue_token:
        for candidate in valid_issues:
            if candidate in {
                "Problem when making payments",
                "Trouble during payment process",
                "Struggling to pay mortgage",
                "Struggling to pay your loan",
            }:
                return candidate

    if "credit report" in issue_token or "your report" in issue_token:
        for candidate in valid_issues:
            if candidate in {
                "Incorrect information on your report",
                "Improper use of your report",
                "Unable to get your credit report or credit score",
                "Problem with a company's investigation into an existing issue",
                "Problem with a company's investigation into an existing problem",
            }:
                return candidate

    raise ValueError(f"Unsupported issue label: {raw_issue!r} for product {raw_product!r}")


def load_holdout_records(dataset_path: Path, limit: int | None = None) -> list[HoldoutRecord]:
    try:
        import pandas as pd  # type: ignore[import-untyped]
    except Exception as error:
        raise RuntimeError("pandas + pyarrow are required to load the holdout parquet file.") from error

    frame = pd.read_parquet(dataset_path)
    required_columns = {"id", "product", "issue", "narrative", "state", "date"}
    missing = sorted(required_columns.difference(frame.columns))
    if missing:
        raise ValueError(f"Holdout parquet is missing required columns: {missing}")

    if limit is not None:
        frame = frame.head(limit)

    records: list[HoldoutRecord] = []
    for row in frame.to_dict(orient="records"):
        raw_product = str(row.get("product") or "")
        raw_issue = str(row.get("issue") or "")
        records.append(
            HoldoutRecord(
                complaint_id=str(row.get("id")),
                complaint_text=str(row.get("narrative") or ""),
                state_code=str(row.get("state") or "XX"),
                date=str(row.get("date") or ""),
                raw_product=raw_product,
                raw_issue=raw_issue,
                truth_product=_normalize_truth_product(raw_product),
                truth_issue=_normalize_truth_issue(raw_product, raw_issue),
            )
        )
    return records


def _tokenize(text: str) -> list[str]:
    return [token for token in _clean_label(text).split() if token]


def _lcs_length(left: list[str], right: list[str]) -> int:
    if not left or not right:
        return 0
    previous = [0] * (len(right) + 1)
    for left_token in left:
        current = [0]
        for index, right_token in enumerate(right, start=1):
            if left_token == right_token:
                current.append(previous[index - 1] + 1)
            else:
                current.append(max(previous[index], current[-1]))
        previous = current
    return previous[-1]


def rouge_l_scores(reference_text: str, candidate_text: str) -> dict[str, float]:
    reference = _tokenize(reference_text)
    candidate = _tokenize(candidate_text)
    if not reference or not candidate:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}
    lcs = _lcs_length(reference, candidate)
    precision = lcs / len(candidate)
    recall = lcs / len(reference)
    if precision == 0.0 and recall == 0.0:
        f1 = 0.0
    else:
        f1 = (2 * precision * recall) / (precision + recall)
    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }


def _safe_divide(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _round4(value: float) -> float:
    return round(value, 4)


def compute_label_metrics(
    rows: Iterable[dict[str, Any]],
    *,
    labels: list[str],
    truth_key: str,
    prediction_key: str,
) -> dict[str, Any]:
    row_list = list(rows)
    breakdown: list[dict[str, Any]] = []
    precisions: list[float] = []
    recalls: list[float] = []
    f1_scores: list[float] = []

    for label in labels:
        support = sum(1 for row in row_list if row[truth_key] == label)
        predicted = sum(1 for row in row_list if row[prediction_key] == label)
        tp = sum(1 for row in row_list if row[truth_key] == label and row[prediction_key] == label)
        if support == 0 and predicted == 0:
            continue
        fp = predicted - tp
        fn = support - tp
        precision = _safe_divide(tp, tp + fp)
        recall = _safe_divide(tp, tp + fn)
        f1 = _safe_divide(2 * precision * recall, precision + recall) if (precision or recall) else 0.0
        precisions.append(precision)
        recalls.append(recall)
        f1_scores.append(f1)
        breakdown.append(
            {
                "label": label,
                "support": support,
                "predicted": predicted,
                "true_positives": tp,
                "precision": _round4(precision),
                "recall": _round4(recall),
                "f1": _round4(f1),
            }
        )

    total = len(row_list)
    accuracy = _safe_divide(sum(1 for row in row_list if row[truth_key] == row[prediction_key]), total)
    return {
        "accuracy": _round4(accuracy),
        "macro_precision": _round4(sum(precisions) / len(precisions)) if precisions else 0.0,
        "macro_recall": _round4(sum(recalls) / len(recalls)) if recalls else 0.0,
        "macro_f1": _round4(sum(f1_scores) / len(f1_scores)) if f1_scores else 0.0,
        "breakdown": breakdown,
    }


def build_grounded_response_reference(
    complaint_text: str,
    root_cause_text: str,
    action_steps: list[str],
    timeline: str,
) -> str:
    pieces = [complaint_text.strip(), root_cause_text.strip(), " ".join(action_steps).strip(), timeline.strip()]
    return "\n".join(piece for piece in pieces if piece)


def summarize_results(rows: list[dict[str, Any]], *, meta: dict[str, Any]) -> dict[str, Any]:
    product_metrics = compute_label_metrics(
        rows,
        labels=PRODUCT_LABELS,
        truth_key="truth_product",
        prediction_key="predicted_product",
    )
    issue_metrics = compute_label_metrics(
        rows,
        labels=ISSUE_LABELS,
        truth_key="truth_issue",
        prediction_key="predicted_issue",
    )

    joint_accuracy = _safe_divide(
        sum(1 for row in rows if row["product_correct"] and row["issue_correct"]),
        len(rows),
    )
    audit_pass_rate = _safe_divide(sum(1 for row in rows if row["audit_verdict"] == "PASS"), len(rows))
    root_cause_clear_rate = _safe_divide(sum(1 for row in rows if row["root_cause_ambiguity_flag"] == "CLEAR"), len(rows))

    row_durations = [float(row["row_duration_seconds"]) for row in rows]
    token_counts = [int(row["total_tokens"]) for row in rows]
    response_rouge_f1 = [float(row["response_grounding_rouge_l"]["f1"]) for row in rows]
    root_cause_rouge_f1 = [float(row["root_cause_rouge_l"]["f1"]) for row in rows]
    evidence_counts = [int(row["root_cause_evidence_count"]) for row in rows]
    rewrite_counts = [int(row["rewrite_count"]) for row in rows]

    return {
        "meta": meta,
        "rows_completed": len(rows),
        "product_classification": product_metrics,
        "issue_classification": issue_metrics,
        "joint_exact_match_accuracy": _round4(joint_accuracy),
        "root_cause": {
            "avg_rouge_l_f1_vs_complaint": _round4(sum(root_cause_rouge_f1) / len(root_cause_rouge_f1)) if root_cause_rouge_f1 else 0.0,
            "avg_evidence_count": _round4(sum(evidence_counts) / len(evidence_counts)) if evidence_counts else 0.0,
            "ambiguity_clear_rate": _round4(root_cause_clear_rate),
        },
        "final_response": {
            "avg_grounding_rouge_l_f1": _round4(sum(response_rouge_f1) / len(response_rouge_f1)) if response_rouge_f1 else 0.0,
            "audit_pass_rate": _round4(audit_pass_rate),
        },
        "runtime": {
            "avg_row_seconds": _round4(sum(row_durations) / len(row_durations)) if row_durations else 0.0,
            "median_row_seconds": _round4(statistics.median(row_durations)) if row_durations else 0.0,
            "p95_row_seconds": _round4(_percentile(row_durations, 0.95)) if row_durations else 0.0,
            "avg_total_tokens": _round4(sum(token_counts) / len(token_counts)) if token_counts else 0.0,
            "avg_rewrite_count": _round4(sum(rewrite_counts) / len(rewrite_counts)) if rewrite_counts else 0.0,
        },
    }


def _percentile(values: list[float], ratio: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(ratio * len(ordered)) - 1))
    return ordered[index]


def _load_existing_results(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def _serialize_step_timings(telemetry: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for item in telemetry:
        output.append(
            {
                "node": str(item.get("node", "")),
                "latency_ms": int(item.get("latency_ms", 0)),
                "model": str(item.get("model", "")),
                "tokens": int(item.get("tokens", 0)),
                "attempts": int(item.get("attempts", 0)),
                "used_fallback": bool(item.get("used_fallback", False)),
                "timestamp": item.get("timestamp"),
            }
        )
    return output


def _evaluate_one(graph: Any, record: HoldoutRecord) -> dict[str, Any]:
    started = time.monotonic()
    final_state = run_complaint(
        graph,
        complaint_text=record.complaint_text,
        state_code=record.state_code or "XX",
    )
    duration = time.monotonic() - started

    classification = final_state.get("classification")
    diagnosis = final_state.get("diagnosis")
    remediation = final_state.get("remediation")
    response_draft = final_state.get("response_draft")
    audit_result = final_state.get("audit_result")
    explanation = final_state.get("explanation")
    telemetry = _serialize_step_timings(list(final_state.get("stage_telemetry") or []))

    if classification is None:
        raise RuntimeError("Pipeline completed without classification output.")

    predicted_product = classification.product_type.value
    predicted_issue = classification.issue_type.value
    product_correct = predicted_product == record.truth_product
    issue_correct = predicted_issue == record.truth_issue

    root_cause_text = diagnosis.root_cause if diagnosis is not None else ""
    evidence_count = len(diagnosis.evidence) if diagnosis is not None else 0
    ambiguity_flag = diagnosis.ambiguity_flag.value if diagnosis is not None else "UNKNOWN"

    action_steps = [step.action for step in remediation.action_plan] if remediation is not None else []
    response_text = response_draft.render_external_response() if response_draft is not None else ""
    timeline_text = response_draft.external.timeline if response_draft is not None else ""
    grounded_reference = build_grounded_response_reference(
        record.complaint_text,
        root_cause_text,
        action_steps,
        timeline_text,
    )

    total_tokens = sum(int(item.get("tokens", 0)) for item in telemetry)
    total_latency_ms = sum(int(item.get("latency_ms", 0)) for item in telemetry)

    return {
        "complaint_id": record.complaint_id,
        "state_code": record.state_code,
        "date": record.date,
        "raw_product": record.raw_product,
        "raw_issue": record.raw_issue,
        "truth_product": record.truth_product,
        "truth_issue": record.truth_issue,
        "predicted_product": predicted_product,
        "predicted_issue": predicted_issue,
        "product_correct": product_correct,
        "issue_correct": issue_correct,
        "joint_exact_match": product_correct and issue_correct,
        "severity": classification.severity.value,
        "compliance_risk": classification.compliance_risk.value,
        "classification_confidence": round(float(classification.confidence), 4),
        "root_cause": root_cause_text,
        "root_cause_evidence_count": evidence_count,
        "root_cause_ambiguity_flag": ambiguity_flag,
        "root_cause_evidence": [item.model_dump(mode="json") for item in (diagnosis.evidence if diagnosis else [])],
        "remediation_status": remediation.status if remediation is not None else "",
        "remediation_route": remediation.route if remediation is not None else "",
        "remediation_action_plan": action_steps,
        "policy_citations": remediation.policy_citations if remediation is not None else {},
        "audit_verdict": audit_result.verdict.value if audit_result is not None else "UNKNOWN",
        "audit_reason_codes": [item.value for item in audit_result.reason_codes] if audit_result is not None else [],
        "audit_critique_summary": audit_result.critique_summary if audit_result is not None else "",
        "rewrite_count": int(final_state.get("rewrite_count", 0)),
        "response_external": response_text,
        "response_internal": response_draft.render_internal_view() if response_draft is not None else "",
        "explanation": explanation.render_text() if explanation is not None else "",
        "response_grounding_rouge_l": rouge_l_scores(grounded_reference, response_text),
        "root_cause_rouge_l": rouge_l_scores(record.complaint_text, root_cause_text),
        "total_tokens": total_tokens,
        "total_latency_ms": total_latency_ms,
        "row_duration_seconds": round(duration, 4),
        "stage_telemetry": telemetry,
        "evaluated_at": datetime.now(UTC).isoformat(),
    }


def _chunked(records: list[HoldoutRecord], batch_size: int) -> Iterable[list[HoldoutRecord]]:
    for index in range(0, len(records), batch_size):
        yield records[index : index + batch_size]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate the full complaint pipeline on holdout.parquet.")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET_PATH), help="Path to holdout parquet dataset.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory for logs, JSONL rows, and summaries.")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="How many rows to evaluate. Use 0 for the full dataset.")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE, help="Rows per summary/checkpoint batch.")
    parser.add_argument("--resume", action="store_true", help="Resume from existing row-level results in the output directory.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    dataset_path = Path(args.dataset)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    results_path = output_dir / "results.jsonl"
    errors_path = output_dir / "errors.jsonl"
    summary_path = output_dir / "summary.json"
    log_path = output_dir / "run.log"

    logger = _setup_logging(log_path)
    logger.info("Loading holdout dataset from %s", dataset_path.as_posix())

    limit = None if args.limit == 0 else args.limit
    records = load_holdout_records(dataset_path, limit=limit)
    logger.info("Loaded %s candidate rows for evaluation", len(records))

    existing_results = _load_existing_results(results_path) if args.resume else []
    completed_ids = {row["complaint_id"] for row in existing_results}
    pending = [record for record in records if record.complaint_id not in completed_ids]

    logger.info("Resume mode: %s | already completed: %s | pending: %s", bool(args.resume), len(completed_ids), len(pending))
    if not pending and existing_results:
        logger.info("No pending rows found. Refreshing summary from existing results.")
        summary = summarize_results(
            existing_results,
            meta={
                "dataset_path": dataset_path.as_posix(),
                "output_dir": output_dir.as_posix(),
                "limit": limit or len(records),
                "batch_size": args.batch_size,
                "resumed": bool(args.resume),
                "updated_at": datetime.now(UTC).isoformat(),
            },
        )
        _write_json(summary_path, summary)
        return 0

    logger.info("Building LangGraph pipeline once for this run")
    graph = build_graph()
    successful_rows = list(existing_results)

    for batch_index, batch in enumerate(_chunked(pending, args.batch_size), start=1):
        logger.info("Starting batch %s with %s rows", batch_index, len(batch))
        for record in batch:
            logger.info("Evaluating complaint_id=%s state=%s", record.complaint_id, record.state_code)
            try:
                result = _evaluate_one(graph, record)
            except Exception as error:  # pragma: no cover - resilience path
                logger.exception("Failed on complaint_id=%s", record.complaint_id)
                _append_jsonl(
                    errors_path,
                    {
                        "complaint_id": record.complaint_id,
                        "error": repr(error),
                        "raw_product": record.raw_product,
                        "raw_issue": record.raw_issue,
                        "state_code": record.state_code,
                        "captured_at": datetime.now(UTC).isoformat(),
                    },
                )
                continue

            _append_jsonl(results_path, result)
            successful_rows.append(result)
            logger.info(
                "Completed complaint_id=%s product_ok=%s issue_ok=%s audit=%s duration=%.2fs",
                record.complaint_id,
                result["product_correct"],
                result["issue_correct"],
                result["audit_verdict"],
                result["row_duration_seconds"],
            )

        summary = summarize_results(
            successful_rows,
            meta={
                "dataset_path": dataset_path.as_posix(),
                "output_dir": output_dir.as_posix(),
                "limit": limit or len(records),
                "batch_size": args.batch_size,
                "resumed": bool(args.resume),
                "updated_at": datetime.now(UTC).isoformat(),
            },
        )
        _write_json(summary_path, summary)
        logger.info(
            "Batch %s summary: rows=%s product_acc=%.4f issue_acc=%.4f joint_acc=%.4f response_rouge_l_f1=%.4f",
            batch_index,
            summary["rows_completed"],
            summary["product_classification"]["accuracy"],
            summary["issue_classification"]["accuracy"],
            summary["joint_exact_match_accuracy"],
            summary["final_response"]["avg_grounding_rouge_l_f1"],
        )

    logger.info("Evaluation run complete. Results saved under %s", output_dir.as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
