import csv
import json
import time
from argparse import ArgumentParser
from pathlib import Path
from typing import Any

from src.graph.pipeline import build_graph, run_complaint

DEFAULT_OUTPUT = Path("outputs/pipeline_results.csv")
DEFAULT_STATE_CODE = "XX"
SAMPLE_COMPLAINT = (
    "Someone stole my identity last week, opened a checking account "
    "using my name, and started transferring money out of my real account. "
    "My name is Jane Smith, SSN 111-22-3333."
)


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())


def _jsonify(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, "model_dump"):
        return json.dumps(value.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def _load_complaints(input_path: Path | None) -> list[dict[str, str]]:
    if input_path is None:
        return [
            {
                "complaint_id": "sample-1",
                "complaint_text": SAMPLE_COMPLAINT,
                "state_code": "NY",
            }
        ]

    suffix = input_path.suffix.lower()
    if suffix != ".csv":
        raise ValueError("Only CSV input is supported here. Use columns: complaint_text, complaint_id, state_code.")

    with input_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        complaints: list[dict[str, str]] = []
        for index, row in enumerate(reader, start=1):
            text = _clean(
                row.get("complaint_text")
                or row.get("narrative")
                or row.get("complaint")
                or row.get("text")
            )
            if not text:
                continue
            complaints.append(
                {
                    "complaint_id": _clean(row.get("complaint_id") or row.get("id") or index),
                    "complaint_text": text,
                    "state_code": _clean(row.get("state_code") or row.get("state") or DEFAULT_STATE_CODE),
                }
            )
    return complaints


def _stage_map(final_state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    telemetry = list(final_state.get("stage_telemetry") or [])
    indexed: dict[str, dict[str, Any]] = {}
    for item in telemetry:
        node = str(item.get("node", ""))
        if node:
            indexed[node] = item
    return indexed


def _join(values: list[Any]) -> str:
    return " | ".join(_clean(value) for value in values if _clean(value))


def _extract_row(
    *,
    complaint_id: str,
    complaint_text: str,
    state_code: str,
    final_state: dict[str, Any] | None,
    error: str,
    wall_time_ms: int,
) -> dict[str, Any]:
    state = final_state or {}
    telemetry = list(state.get("stage_telemetry") or [])
    stage_map = _stage_map(state)

    intake = state.get("intake")
    classification = state.get("classification")
    diagnosis = state.get("diagnosis")
    remediation = state.get("remediation")
    audit_result = state.get("audit_result")
    explanation = state.get("explanation")
    response_draft = state.get("response_draft")

    row: dict[str, Any] = {
        "complaint_id": complaint_id,
        "state_code": state_code,
        "status": "failed" if error else "completed",
        "error": error,
        "thread_id": state.get("thread_id", ""),
        "wall_time_ms": wall_time_ms,
        "rewrite_count": state.get("rewrite_count", 0),
        "event_count": len(state.get("events") or []),
        "total_stage_latency_ms": sum(int(item.get("latency_ms", 0)) for item in telemetry),
        "total_stage_tokens": sum(int(item.get("tokens", 0)) for item in telemetry),
        "total_stage_attempts": sum(int(item.get("attempts", 0)) for item in telemetry),
        "fallback_stages": _join(
            [item.get("node", "") for item in telemetry if bool(item.get("used_fallback"))]
        ),
        "raw_complaint": complaint_text,
        "scrubbed_text": getattr(intake, "scrubbed_text", ""),
        "product_type": getattr(classification, "product_type", ""),
        "issue_type": getattr(classification, "issue_type", ""),
        "severity": getattr(classification, "severity", ""),
        "compliance_risk": getattr(classification, "compliance_risk", ""),
        "classification_confidence": getattr(classification, "confidence", ""),
        "root_cause": getattr(diagnosis, "root_cause", ""),
        "root_cause_evidence_ids": _join(
            [item.citation.id for item in getattr(diagnosis, "evidence", [])]
        ),
        "remediation_status": getattr(remediation, "status", ""),
        "remediation_route": getattr(remediation, "route", ""),
        "remediation_actions": _join(
            [step.action for step in getattr(remediation, "action_plan", [])]
        ),
        "audit_verdict": getattr(audit_result, "verdict", ""),
        "audit_reason_codes": _join(getattr(audit_result, "reason_codes", [])),
        "audit_must_fix_items": _join(getattr(audit_result, "must_fix_items", [])),
        "final_response": response_draft.render_text() if response_draft else "",
        "final_explanation": explanation.render_text() if explanation else "",
        "stage_telemetry_json": json.dumps(telemetry, ensure_ascii=False, sort_keys=True),
        "classification_json": _jsonify(classification),
        "diagnosis_json": _jsonify(diagnosis),
        "remediation_json": _jsonify(remediation),
        "audit_result_json": _jsonify(audit_result),
        "response_draft_json": _jsonify(response_draft),
        "explanation_json": _jsonify(explanation),
    }

    for stage_name in (
        "intake",
        "product_classifier",
        "issue_classifier",
        "root_cause",
        "remediator",
        "response_writer",
        "response_auditor",
        "explainer",
    ):
        item = stage_map.get(stage_name, {})
        row[f"{stage_name}_model"] = item.get("model", "")
        row[f"{stage_name}_latency_ms"] = item.get("latency_ms", 0)
        row[f"{stage_name}_tokens"] = item.get("tokens", 0)
        row[f"{stage_name}_attempts"] = item.get("attempts", 0)
        row[f"{stage_name}_used_fallback"] = item.get("used_fallback", False)

    return row


def run_batch(input_path: Path | None, output_path: Path) -> Path:
    print("Building the FinComplaint LangGraph pipeline...")
    graph = build_graph()
    complaints = _load_complaints(input_path)
    if not complaints:
        raise ValueError("No complaints found to run.")

    total = len(complaints)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    wrote_header = False

    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer: csv.DictWriter[str] | None = None

        for index, complaint in enumerate(complaints, start=1):
            complaint_id = complaint["complaint_id"]
            complaint_text = complaint["complaint_text"]
            state_code = complaint["state_code"] or DEFAULT_STATE_CODE

            print(f"[progress] {index}/{total} running complaint_id={complaint_id}")
            started = time.monotonic()
            final_state: dict[str, Any] | None = None
            error = ""

            try:
                final_state = run_complaint(
                    graph,
                    complaint_text=complaint_text,
                    state_code=state_code,
                )
            except Exception as exc:
                error = str(exc)

            wall_time_ms = int((time.monotonic() - started) * 1000)
            row = _extract_row(
                complaint_id=complaint_id,
                complaint_text=complaint_text,
                state_code=state_code,
                final_state=final_state,
                error=error,
                wall_time_ms=wall_time_ms,
            )

            if writer is None:
                writer = csv.DictWriter(handle, fieldnames=list(row.keys()))
            if not wrote_header:
                writer.writeheader()
                wrote_header = True
            writer.writerow(row)
            handle.flush()

            print(
                f"[progress] {index}/{total} done complaint_id={complaint_id} "
                f"status={'failed' if error else 'completed'} wall_time_ms={wall_time_ms}"
            )

    print(f"[done] Stored {total} results in {output_path}")
    return output_path


def main() -> None:
    parser = ArgumentParser(description="Run the pipeline for one or more complaints and store outputs in CSV.")
    parser.add_argument("--input", help="Optional CSV file with complaint_text, complaint_id, and state_code.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    run_batch(
        input_path=Path(args.input) if args.input else None,
        output_path=Path(args.output),
    )


if __name__ == "__main__":
    main()
