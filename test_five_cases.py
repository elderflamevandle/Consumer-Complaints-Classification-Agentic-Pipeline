"""Run 5 complaint cases through the full pipeline.

Each test case is explicitly tied to a product + issue from src/schemas/taxonomy.py.
After each run the classifier output is compared against the expected taxonomy entry
so you can see immediately whether the pipeline classified correctly.
"""

from __future__ import annotations

import sys
import time

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.graph.pipeline import build_graph
from src.schemas.taxonomy import PRODUCT_ISSUE_HIERARCHY, PRODUCT_DISPLAY_NAMES

# ---------------------------------------------------------------------------
# Pull exact strings from the taxonomy — no hardcoding
# ---------------------------------------------------------------------------

_CHK = "CHECKING_SAVINGS_ACCOUNT"
_CC  = "CREDIT_CARD"
_MTG = "MORTGAGE"
_DC  = "DEBT_COLLECTION"
_MT  = "MONEY_TRANSFER"
_CR  = "CREDIT_REPORTING"
_VL  = "VEHICLE_LOAN_LEASE"

# Each tuple: (product_key, issue_display_string)
# Issue strings are taken verbatim from PRODUCT_ISSUE_HIERARCHY
_PICKS = [
    (_CHK, "Problem with a lender or other company charging your account"),
    (_CC,  "Fees or interest"),
    (_MTG, "Struggling to pay mortgage"),
    (_DC,  "Attempts to collect debt not owed"),
    (_MT,  "Fraud or scam"),
]

# Validate all picks exist in the taxonomy at import time
for _prod, _issue in _PICKS:
    assert _prod in PRODUCT_ISSUE_HIERARCHY, f"Unknown product key: {_prod}"
    assert _issue in PRODUCT_ISSUE_HIERARCHY[_prod], (
        f"Issue '{_issue}' not in {_prod}. Valid options:\n"
        + "\n".join(f"  - {i}" for i in PRODUCT_ISSUE_HIERARCHY[_prod])
    )

# ---------------------------------------------------------------------------
# Test cases — complaint texts are written to clearly match the taxonomy pick
# ---------------------------------------------------------------------------

TEST_CASES = [
        {
        "id":         "TC-01",
        "product":    _PICKS[2][0],
        "issue":      _PICKS[2][1],
        "state_code": "FL",
        "complaint": (
            "I have been unable to make my mortgage payments after a medical emergency wiped out "
            "my savings. I submitted a hardship application for loan modification three months ago "
            "but my servicer has not assigned a single point of contact and keeps losing my documents. "
            "They sent a notice of default last week and I am afraid I will lose my home."
        ),
    },
    {
        "id":         "TC-02",
        "product":    _PICKS[1][0],
        "issue":      _PICKS[1][1],
        "state_code": "TX",
        "complaint": (
            "My credit card company charged me a 29% penalty APR and a $39 late fee even though "
            "my payment was only one day late due to a bank processing delay — not my fault. "
            "They also retroactively applied the penalty rate to my existing balance without "
            "giving me 45 days notice as required. I want the fees reversed and the rate restored."
        ),
    },
    {
        "id":         "TC-03",
        "product":    _PICKS[0][0],
        "issue":      _PICKS[0][1],
        "state_code": "CA",
        "complaint": (
            "My bank has been debiting an unauthorised $45 overdraft protection fee from my "
            "checking account every month for six months. I never opted in to this service and "
            "have asked them three times to stop and refund the charges. The deductions continue "
            "and the customer service team keeps telling me to call back later."
        ),
    },
    {
        "id":         "TC-04",
        "product":    _PICKS[3][0],
        "issue":      _PICKS[3][1],
        "state_code": "NY",
        "complaint": (
            "A debt collector is demanding $2,400 for a store credit card I never opened. "
            "I have never had an account with this retailer and the address they have on file "
            "is not mine. I sent a written debt validation request 40 days ago but they have "
            "not responded and are still reporting this fraudulent debt to the credit bureaus."
        ),
    },
    {
        "id":         "TC-05",
        "product":    _PICKS[4][0],
        "issue":      _PICKS[4][1],
        "state_code": "WA",
        "complaint": (
            "I was tricked into sending $800 through a peer-to-peer payment app to a scammer "
            "posing as a landlord for an apartment that does not exist. I reported the fraud to "
            "the app within 10 minutes of the transfer but they refused to reverse it, saying "
            "all transactions are final. This was clearly a scam and I want my money back."
        ),
    },
]

DIVIDER = "=" * 70
SECTION  = "-" * 70

# Friendly labels for each LangGraph node name
_NODE_LABELS = {
    "intake_processor":   "[1] INTAKE",
    "product_classifier": "[2] PRODUCT CLASSIFIER",
    "issue_classifier":   "[3] ISSUE CLASSIFIER",
    "root_cause":         "[4] ROOT CAUSE",
    "remediator":         "[5] REMEDIATOR + MCP",
    "response_writer":    "[6] WRITER",
    "response_auditor":   "[7] AUDITOR",
    "explainer":          "[8] EXPLAINER",
}


def _run_with_step_timing(graph, complaint_text: str, state_code: str) -> tuple[dict, list[tuple[str, float]]]:
    """Run pipeline via .stream() and capture per-node wall-clock seconds.

    Returns (final_state, step_timings) where step_timings is a list of
    (node_name, seconds) in execution order.
    """
    import uuid
    tid = str(uuid.uuid4())
    initial_state = {
        "thread_id": tid,
        "raw_complaint": complaint_text,
        "state_code": state_code,
        "rewrite_count": 0,
        "events": [],
        "stage_telemetry": [],
        "unresolved_issues": [],
    }
    run_config = {"configurable": {"thread_id": tid}}

    step_timings: list[tuple[str, float]] = []
    final_state: dict = dict(initial_state)
    prev_time = time.monotonic()

    for chunk in graph.stream(initial_state, config=run_config):
        now = time.monotonic()
        for node_name in chunk:
            elapsed = now - prev_time
            step_timings.append((node_name, elapsed))
            final_state.update(chunk[node_name])
        prev_time = now

    return final_state, step_timings


def _match_label(expected: str, actual: str) -> str:
    return "MATCH" if expected.strip().lower() == actual.strip().lower() else "MISMATCH"


def print_step_timings(step_timings: list[tuple[str, float]]) -> None:
    """Print a table of per-step execution times."""
    print("\n  STEP TIMING BREAKDOWN")
    print(SECTION)
    print(f"  {'Step':<30} {'Time (s)':>10}")
    print(f"  {'-'*29} {'-'*10}")
    total = 0.0
    for node_name, secs in step_timings:
        label = _NODE_LABELS.get(node_name, node_name)
        print(f"  {label:<30} {secs:>10.2f}")
        total += secs
    print(f"  {'-'*29} {'-'*10}")
    print(f"  {'TOTAL':<30} {total:>10.2f}")


def print_agent_output(case: dict, final_state: dict) -> None:
    expected_product = case["product"]
    expected_issue   = case["issue"]

    intake         = final_state.get("intake")
    classification = final_state.get("classification")
    diagnosis      = final_state.get("diagnosis")
    remediation    = final_state.get("remediation")
    audit_result   = final_state.get("audit_result")
    response_draft = final_state.get("response_draft")
    explanation    = final_state.get("explanation")
    telemetry      = list(final_state.get("stage_telemetry") or [])

    # 1. Intake
    print("\n  [1] INTAKE AGENT — PII Scrubbing")
    print(SECTION)
    if intake:
        print(f"  Scrubbed : {intake.scrubbed_text}")
    else:
        print("  No intake result.")

    # 2. Classifier — show expected vs actual
    print("\n  [2] CLASSIFIER AGENTS")
    print(SECTION)
    if classification:
        actual_product = classification.product_type.value
        actual_issue   = classification.issue_type.value
        product_match  = _match_label(expected_product, actual_product)
        issue_match    = _match_label(expected_issue,   actual_issue)

        print(f"  Expected Product : {PRODUCT_DISPLAY_NAMES.get(expected_product, expected_product)}")
        print(f"  Actual Product   : {PRODUCT_DISPLAY_NAMES.get(actual_product, actual_product)}")
        print(f"  Product Match    : [{product_match}]")
        print()
        print(f"  Expected Issue   : {expected_issue}")
        print(f"  Actual Issue     : {actual_issue}")
        print(f"  Issue Match      : [{issue_match}]")
        print()
        print(f"  Severity         : {classification.severity.value}")
        print(f"  Compliance Risk  : {classification.compliance_risk.value}")
        print(f"  Confidence       : {classification.confidence:.0%}")
    else:
        print("  No classification result.")

    # 3. Root Cause
    print("\n  [3] ROOT CAUSE AGENT — RAG / Historical CFPB Cases")
    print(SECTION)
    if diagnosis:
        print(f"  Root Cause : {diagnosis.root_cause}")
        if diagnosis.evidence:
            print(f"  Evidence   : {' | '.join(e.citation.id for e in diagnosis.evidence)}")
    else:
        print("  No diagnosis result.")

    # 4. Remediator + MCP
    print("\n  [4] MCP SERVER + REMEDIATOR AGENT")
    print(SECTION)
    if remediation:
        print(f"  Status     : {remediation.status}")
        print(f"  Route      : {remediation.route}")
        cit = remediation.policy_citations
        print(f"  SLA Window : {cit.get('sla_window', 'N/A')}")
        print(f"  Regulation : {cit.get('regulatory_basis', 'N/A')}")
        if remediation.action_plan:
            print("  Actions    :")
            for step in remediation.action_plan:
                print(f"    {step.order}. {step.action}")
        else:
            print("  Actions    : None — routed to human review")
    else:
        print("  No remediation result.")

    # 5. Auditor
    print("\n  [5] AUDITOR AGENT")
    print(SECTION)
    if audit_result:
        print(f"  Verdict    : {audit_result.verdict}")
        codes = getattr(audit_result, "reason_codes", [])
        if codes:
            print(f"  Reason Codes : {' | '.join(codes)}")
    print(f"  Rewrites   : {final_state.get('rewrite_count', 0)}")

    # 6. Writer
    print("\n  [6] WRITER AGENT — Final Customer Response")
    print(SECTION)
    if response_draft:
        try:
            rendered = response_draft.render_text()
        except Exception:
            rendered = str(response_draft)
        for line in rendered.splitlines():
            print(f"  {line}")
    else:
        print("  No response draft.")

    # 7. Explainer
    print("\n  [7] EXPLAINER AGENT — Audit Trail")
    print(SECTION)
    if explanation:
        try:
            rendered = explanation.render_text()
        except Exception:
            rendered = str(explanation)
        for line in rendered.splitlines():
            print(f"  {line}")
    else:
        print("  No explanation.")

    # Telemetry
    if telemetry:
        total_tokens  = sum(int(t.get("tokens",     0)) for t in telemetry)
        total_latency = sum(int(t.get("latency_ms", 0)) for t in telemetry)
        fallbacks     = [t["node"] for t in telemetry if t.get("used_fallback")]
        print(f"\n  Tokens : {total_tokens:,}  |  Latency : {total_latency:,} ms", end="")
        if fallbacks:
            print(f"  |  Fallbacks : {', '.join(fallbacks)}", end="")
        print()


def main() -> None:
    print(DIVIDER)
    print("  FinComplaint AI — 5 Taxonomy-Grounded Pipeline Tests")
    print(DIVIDER)

    # Print the taxonomy picks being tested
    print("\n  Test matrix (from src/schemas/taxonomy.py):")
    for i, case in enumerate(TEST_CASES, start=1):
        prod_label  = PRODUCT_DISPLAY_NAMES.get(case["product"], case["product"])
        print(f"  {case['id']}  {prod_label}")
        print(f"        Issue : {case['issue']}")
        print(f"        State : {case['state_code']}")

    print(f"\n  Building LangGraph pipeline...")
    graph = build_graph()
    print("  Pipeline ready.\n")

    summary: list[tuple[str, str, bool, bool, bool]] = []
    # (id, label, pipeline_passed, product_match, issue_match)

    for i, case in enumerate(TEST_CASES, start=1):
        prod_label = PRODUCT_DISPLAY_NAMES.get(case["product"], case["product"])

        print(f"\n{DIVIDER}")
        print(f"  CASE {i}/{len(TEST_CASES)} — {case['id']}  |  {prod_label}  |  State: {case['state_code']}")
        print(DIVIDER)
        print(f"\n  Complaint:\n  {case['complaint']}\n")

        started    = time.monotonic()
        final_state = None
        step_timings: list[tuple[str, float]] = []
        passed      = False
        prod_match  = False
        issue_match = False

        try:
            final_state, step_timings = _run_with_step_timing(
                graph,
                complaint_text=case["complaint"],
                state_code=case["state_code"],
            )
            print_agent_output(case, final_state)
            print_step_timings(step_timings)

            classification = final_state.get("classification")
            if classification:
                prod_match  = _match_label(case["product"], classification.product_type.value) == "MATCH"
                issue_match = _match_label(case["issue"],   classification.issue_type.value)   == "MATCH"
            passed = True

        except Exception as exc:
            print(f"\n  ERROR: {exc}")

        wall_ms = int((time.monotonic() - started) * 1000)
        status  = "PASSED" if passed else "FAILED"
        print(f"\n  [{status}]  {case['id']} completed in {wall_ms:,} ms")
        summary.append((case["id"], prod_label, passed, prod_match, issue_match))

    # Final summary table
    print(f"\n{DIVIDER}")
    print("  FINAL SUMMARY")
    print(DIVIDER)
    print(f"  {'ID':<8} {'Pipeline':<10} {'Product':<10} {'Issue':<10}  Label")
    print(f"  {'-'*7} {'-'*9} {'-'*9} {'-'*9}  {'-'*35}")
    for case_id, label, passed, pm, im in summary:
        p_status  = "PASS" if passed else "FAIL"
        pm_status = "MATCH" if pm else "MISS"
        im_status = "MATCH" if im else "MISS"
        print(f"  {case_id:<8} {p_status:<10} {pm_status:<10} {im_status:<10}  {label}")

    total_pass    = sum(1 for *_, p, _, _ in summary if p)
    product_match = sum(1 for *_, _, pm, _ in summary if pm)
    issue_match   = sum(1 for *_, _, _, im in summary if im)
    print(f"\n  Pipeline : {total_pass}/{len(summary)} passed")
    print(f"  Product  : {product_match}/{len(summary)} correctly classified")
    print(f"  Issue    : {issue_match}/{len(summary)} correctly classified")
    print(DIVIDER)


if __name__ == "__main__":
    main()
