"""
Mock AI pipeline — simulates all 8 nodes of the real fincomplaint_ai pipeline
with realistic latency, structured outputs, and async streaming updates via
an asyncio.Queue that WebSocket handlers can consume.

Each node emits a PipelineUpdate onto the queue as it starts and completes.
The mock runs the full pipeline unless it hits a HITL interrupt condition.
"""

from __future__ import annotations

import asyncio
import logging
import random
import re
from datetime import datetime
from typing import Any, AsyncIterator, Dict, List, Optional

from ..config import settings
from ..models.complaint import (
    ClassificationResult,
    ComplaintStatus,
    ComplianceRisk,
    RemediationStep,
    SeverityLevel,
)

logger = logging.getLogger(__name__)

# ── Pipeline node definitions ─────────────────────────────────────────────────

PIPELINE_NODES: List[str] = [
    "intake",
    "classifier",
    "routing",
    "root_cause",
    "remediator",
    "writer",
    "auditor",
    "explainer",
]

# ── PII patterns for mock scrubbing ─────────────────────────────────────────

_PII_PATTERNS = [
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[SSN-REDACTED]"),
    (re.compile(r"\b\d{16}\b"), "[CC-REDACTED]"),
    (re.compile(r"\b\d{4}[\s-]\d{4}[\s-]\d{4}[\s-]\d{4}\b"), "[CC-REDACTED]"),
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[a-z]{2,}\b"), "[EMAIL-REDACTED]"),
    (re.compile(r"\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b"), "[PHONE-REDACTED]"),
]


def _scrub_pii(text: str) -> tuple[str, int]:
    redacted = 0
    for pattern, replacement in _PII_PATTERNS:
        new_text, n = re.subn(pattern, replacement, text)
        redacted += n
        text = new_text
    return text, redacted


# ── Classification heuristics ─────────────────────────────────────────────────

def _classify(text: str) -> ClassificationResult:
    lowered = text.lower()

    product = "CREDIT_CARD"
    if "mortgage" in lowered:
        product = "MORTGAGE"
    elif "loan" in lowered:
        product = "LOAN"
    elif any(w in lowered for w in ("checking", "savings", "bank account")):
        product = "BANK_ACCOUNT"
    elif any(w in lowered for w in ("debt", "collector", "collection")):
        product = "DEBT_COLLECTION"
    elif any(w in lowered for w in ("transfer", "wire", "zelle", "venmo")):
        product = "MONEY_TRANSFER"

    issue = "BILLING"
    if any(w in lowered for w in ("fraud", "scam", "stolen")):
        issue = "FRAUD"
    elif any(w in lowered for w in ("identity theft", "identity", "impersonat")):
        issue = "IDENTITY_THEFT"
    elif any(w in lowered for w in ("payment", "late payment", "overdue")):
        issue = "PAYMENT"
    elif any(w in lowered for w in ("credit report", "bureau", "experian", "equifax")):
        issue = "CREDIT_REPORTING"
    elif any(w in lowered for w in ("representative", "customer service", "hold")):
        issue = "CUSTOMER_SERVICE"

    severity = SeverityLevel.LOW
    compliance_risk = ComplianceRisk.LOW
    confidence = round(random.uniform(0.68, 0.94), 2)

    critical_words = ("lawsuit", "identity theft", "illegal", "attorney")
    high_words = ("fraud", "unauthorized", "harassment", "foreclosure")

    if any(w in lowered for w in critical_words):
        severity = SeverityLevel.CRITICAL
        compliance_risk = ComplianceRisk.HIGH
        confidence = round(random.uniform(0.88, 0.97), 2)
    elif any(w in lowered for w in high_words):
        severity = SeverityLevel.HIGH
        compliance_risk = ComplianceRisk.HIGH
        confidence = round(random.uniform(0.78, 0.92), 2)
    elif any(w in lowered for w in ("billing", "charged", "fee")):
        severity = SeverityLevel.MEDIUM
        compliance_risk = ComplianceRisk.MEDIUM

    return ClassificationResult(
        product_type=product,
        issue_type=issue,
        severity=severity,
        compliance_risk=compliance_risk,
        confidence=confidence,
    )


# ── Update message ─────────────────────────────────────────────────────────────

class PipelineUpdate:
    __slots__ = ("node", "event", "payload", "timestamp")

    def __init__(self, node: str, event: str, payload: Dict[str, Any]):
        self.node = node
        self.event = event           # "started" | "completed" | "failed" | "interrupted"
        self.payload = payload
        self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "pipeline_update",
            "node": self.node,
            "event": self.event,
            "payload": self.payload,
            "timestamp": self.timestamp,
        }


# ── Mock runner ───────────────────────────────────────────────────────────────

class MockPipelineRunner:
    """
    Runs the full mock pipeline for a single complaint.
    Yields PipelineUpdate objects that callers can forward to WebSocket clients.
    Writes intermediate results back through the callback so the DB stays updated.
    """

    def __init__(
        self,
        complaint_id: str,
        complaint_text: str,
        state_code: str = "CA",
        delay: float = settings.pipeline_mock_delay_seconds,
    ):
        self.complaint_id = complaint_id
        self.complaint_text = complaint_text
        self.state_code = state_code
        self.delay = delay
        self._result: Dict[str, Any] = {}

    async def run(self) -> AsyncIterator[PipelineUpdate]:
        """Async generator — yield each update as it happens."""
        text = self.complaint_text

        # ── NODE 1: INTAKE ────────────────────────────────────────────────────
        yield PipelineUpdate("intake", "started", {"message": "Scrubbing PII from complaint text"})
        await asyncio.sleep(self.delay)

        scrubbed, pii_count = _scrub_pii(text)
        self._result["scrubbed_text"] = scrubbed
        self._result["pii_redacted_count"] = pii_count

        yield PipelineUpdate("intake", "completed", {
            "scrubbed_text": scrubbed[:200] + "…" if len(scrubbed) > 200 else scrubbed,
            "pii_redacted_count": pii_count,
            "latency_ms": int(self.delay * 1000),
        })

        # ── NODE 2: CLASSIFIER ────────────────────────────────────────────────
        yield PipelineUpdate("classifier", "started", {"message": "Classifying complaint with LLM"})
        await asyncio.sleep(self.delay * 1.5)

        classification = _classify(scrubbed)
        self._result["classification"] = classification.model_dump()

        yield PipelineUpdate("classifier", "completed", {
            "classification": classification.model_dump(),
            "model": "llama-3.3-70b-versatile (mock)",
            "latency_ms": int(self.delay * 1500),
            "tokens_used": random.randint(180, 320),
        })

        # ── NODE 3: ROUTING ───────────────────────────────────────────────────
        yield PipelineUpdate("routing", "started", {"message": "Evaluating routing decision"})
        await asyncio.sleep(self.delay * 0.5)

        needs_review = (
            classification.confidence < 0.72
            or classification.compliance_risk == ComplianceRisk.HIGH
            or classification.severity == SeverityLevel.CRITICAL
        )
        self._result["review_required"] = needs_review
        route = "human_review" if needs_review else "continue"

        yield PipelineUpdate("routing", "completed", {
            "route": route,
            "review_required": needs_review,
            "reason": (
                "High compliance risk or critical severity" if needs_review
                else "Auto-approved based on confidence and risk"
            ),
        })

        if needs_review:
            self._result["status"] = ComplaintStatus.INTERRUPTED
            yield PipelineUpdate("routing", "interrupted", {
                "message": "Human review required before pipeline can continue",
                "allowed_actions": ["approve", "edit", "reject"],
                "classification": classification.model_dump(),
            })
            return   # Pipeline pauses here; resumes via /review endpoint

        # ── NODE 4: ROOT CAUSE ────────────────────────────────────────────────
        yield PipelineUpdate("root_cause", "started", {
            "message": "Retrieving similar cases from vector store"
        })
        await asyncio.sleep(self.delay * 2)

        root_cause_text = _mock_root_cause(classification.issue_type)
        evidence = _mock_evidence(classification.issue_type)
        self._result["root_cause"] = root_cause_text
        self._result["root_cause_evidence"] = evidence

        yield PipelineUpdate("root_cause", "completed", {
            "root_cause": root_cause_text,
            "evidence_count": len(evidence),
            "ambiguity_flag": "CLEAR",
            "model": "bge-large-en-v1.5 + llama-3.3-70b (mock)",
            "latency_ms": int(self.delay * 2000),
            "tokens_used": random.randint(380, 520),
        })

        # ── NODE 5: REMEDIATOR ────────────────────────────────────────────────
        yield PipelineUpdate("remediator", "started", {
            "message": "Querying MCP policy server for SLA requirements"
        })
        await asyncio.sleep(self.delay * 1.8)

        steps, citations = _mock_remediation(classification.issue_type, self.state_code)
        self._result["remediation_steps"] = [s.model_dump() for s in steps]
        self._result["policy_citations"] = citations
        assigned_team = _assign_team(classification.issue_type)
        self._result["assigned_team"] = assigned_team

        yield PipelineUpdate("remediator", "completed", {
            "action_plan": [s.action for s in steps],
            "policy_citations": citations,
            "assigned_team": assigned_team,
            "model": "llama-3.3-70b + MCP policy server (mock)",
            "latency_ms": int(self.delay * 1800),
            "tokens_used": random.randint(320, 460),
        })

        # ── NODE 6: WRITER ────────────────────────────────────────────────────
        yield PipelineUpdate("writer", "started", {
            "message": "Drafting regulatory-compliant response letter"
        })
        await asyncio.sleep(self.delay * 2.2)

        response_draft = _mock_response_draft(
            classification.issue_type, steps, self.state_code
        )
        self._result["response_draft"] = response_draft

        yield PipelineUpdate("writer", "completed", {
            "response_draft_preview": response_draft[:300] + "…",
            "model": "llama-3.3-70b-versatile (mock)",
            "latency_ms": int(self.delay * 2200),
            "tokens_used": random.randint(440, 620),
        })

        # ── NODE 7: AUDITOR ───────────────────────────────────────────────────
        yield PipelineUpdate("auditor", "started", {
            "message": "Running compliance audit on response draft"
        })
        await asyncio.sleep(self.delay * 1.4)

        # 90% pass rate in mock
        audit_pass = random.random() > 0.10
        verdict = "PASS" if audit_pass else "FAIL"
        fail_codes: List[str] = [] if audit_pass else ["MISSING_SLA_REFERENCE", "DISCLOSURE_INCOMPLETE"]
        self._result["audit_verdict"] = verdict

        yield PipelineUpdate("auditor", "completed", {
            "verdict": verdict,
            "fail_codes": fail_codes,
            "cycles": 1 if audit_pass else 2,
            "model": "llama-3.3-70b-versatile (mock)",
            "latency_ms": int(self.delay * 1400),
        })

        # ── NODE 8: EXPLAINER ─────────────────────────────────────────────────
        yield PipelineUpdate("explainer", "started", {
            "message": "Generating explanation chain for regulators"
        })
        await asyncio.sleep(self.delay * 1.2)

        explanation = _mock_explanation(classification, root_cause_text, verdict)
        self._result["explanation"] = explanation
        self._result["status"] = ComplaintStatus.COMPLETE

        yield PipelineUpdate("explainer", "completed", {
            "explanation_preview": explanation[:400] + "…",
            "model": "llama-3.3-70b-versatile (mock)",
            "latency_ms": int(self.delay * 1200),
            "tokens_used": random.randint(280, 400),
        })

    @property
    def final_result(self) -> Dict[str, Any]:
        return self._result


# ── Content generators ────────────────────────────────────────────────────────

def _mock_root_cause(issue_type: str) -> str:
    causes = {
        "FRAUD": (
            "Root cause analysis identified a pattern of unauthorized card-not-present "
            "transactions consistent with card data compromise. Similar cases (similarity "
            "score ≥ 0.87) show a recurring failure in real-time fraud scoring for "
            "cross-border e-commerce transactions in the $50–$300 range."
        ),
        "BILLING": (
            "Evidence from 5 retrieved similar complaints points to a systematic "
            "double-billing defect introduced in the billing engine during the Q3 "
            "system migration. The failure is concentrated on accounts with auto-pay "
            "enabled and a billing cycle date between the 1st and 5th of the month."
        ),
        "IDENTITY_THEFT": (
            "Cross-reference with historical cases reveals a credential-stuffing pattern "
            "using leaked credentials from a third-party breach. The primary root cause "
            "is insufficient MFA enforcement on account recovery flows."
        ),
        "PAYMENT": (
            "Retrieved evidence shows recurring late-payment misclassification stemming "
            "from a timezone normalisation bug in the payment gateway integration "
            "affecting transactions submitted between 11:45 PM–midnight EST."
        ),
        "CREDIT_REPORTING": (
            "Similar complaints indicate a data-furnisher synchronisation delay where "
            "resolved disputes are not propagating to all three bureaus within the "
            "FCRA-mandated 30-day window due to a batch-processing bottleneck."
        ),
        "CUSTOMER_SERVICE": (
            "Pattern analysis of similar cases reveals inadequate first-call resolution "
            "training for the offshore support team handling digital banking escalations, "
            "combined with a missing knowledge-base entry for this product change."
        ),
    }
    return causes.get(issue_type, (
        "Root cause analysis completed. The predominant pattern across retrieved "
        "similar complaints suggests a process gap in the complaint handling workflow "
        "that requires review by the responsible team."
    ))


def _mock_evidence(issue_type: str) -> List[Dict[str, Any]]:
    return [
        {
            "rank": i + 1,
            "summary": f"Similar {issue_type} complaint resolved in {random.randint(3, 14)} days "
                       f"via {'refund' if i % 2 == 0 else 'account credit'} remediation.",
            "citation": {
                "id": f"CFPB-{random.randint(100000, 999999)}",
                "product": "CREDIT_CARD",
                "issue": issue_type,
                "date": f"2024-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
            },
            "score": round(random.uniform(0.78, 0.96), 4),
        }
        for i in range(5)
    ]


def _mock_remediation(
    issue_type: str, state_code: str
) -> tuple[List[RemediationStep], Dict[str, Any]]:
    plans = {
        "FRAUD": [
            "Immediately suspend all pending transactions on the affected account",
            "Initiate provisional credit within 5 business days per Regulation E",
            "Issue replacement card with new card number within 3 business days",
            "File Suspicious Activity Report (SAR) if loss exceeds $5,000",
            "Complete fraud investigation within 10 business days and provide written findings",
        ],
        "BILLING": [
            "Reverse duplicate charge and issue credit within 1 business day",
            "Send written billing correction notice per TILA requirements",
            "Audit affected billing batch for other impacted accounts",
            "Provide account statement showing correction to customer",
            "Implement preventive control in billing engine within 30 days",
        ],
        "IDENTITY_THEFT": [
            "Freeze account and issue fraud alert immediately",
            "Send Identity Theft Report documentation request to customer",
            "Block all unauthorised accounts opened in customer's name",
            "Provide free credit monitoring for 12 months",
            "Coordinate with credit bureaus to block fraudulent tradelines within 4 business days",
        ],
        "PAYMENT": [
            "Reverse any late fees charged due to the misclassified payment",
            "Correct payment posting date in customer account ledger",
            "Provide written confirmation of correction within 5 business days",
            "Notify credit bureaus of corrected payment status",
        ],
        "CREDIT_REPORTING": [
            "Submit dispute correction to all three bureaus within 5 business days",
            "Provide customer with FCRA dispute acknowledgment letter",
            "Complete investigation and notify bureaus of result within 30 days",
            "Send customer written notice of dispute resolution",
        ],
        "CUSTOMER_SERVICE": [
            "Escalate to senior resolution specialist within 1 business day",
            "Provide customer with direct callback from supervisor",
            "Document root cause and update knowledge base",
            "Follow up with written resolution summary within 5 business days",
        ],
    }
    actions = plans.get(issue_type, [
        "Acknowledge complaint and assign to responsible team",
        "Complete investigation within regulatory timeframe",
        "Provide written resolution to customer",
    ])
    steps = [
        RemediationStep(order=i + 1, action=a, policy_reference=_policy_ref(issue_type))
        for i, a in enumerate(actions)
    ]
    citations = {
        "sla_window": _sla_window(issue_type),
        "required_actions": actions[:3],
        "regulatory_basis": _policy_ref(issue_type),
        "state_specific": f"{state_code} Financial Code §{random.randint(1000, 9999)}",
    }
    return steps, citations


def _policy_ref(issue_type: str) -> str:
    refs = {
        "FRAUD": "Regulation E (12 CFR §1005), FCBA",
        "BILLING": "Truth in Lending Act (TILA), 12 CFR §1026.13",
        "IDENTITY_THEFT": "FCRA §605B, FTC Red Flags Rule",
        "PAYMENT": "Regulation E (12 CFR §1005.11)",
        "CREDIT_REPORTING": "FCRA §611, 12 CFR §1022.43",
        "CUSTOMER_SERVICE": "CFPB Supervision and Examination Manual",
    }
    return refs.get(issue_type, "CFPB Complaint Resolution Guidelines")


def _sla_window(issue_type: str) -> str:
    windows = {
        "FRAUD": "10 business days (provisional credit within 5)",
        "BILLING": "5 business days for credit; 30 days for investigation",
        "IDENTITY_THEFT": "4 business days for block; 30 days investigation",
        "PAYMENT": "5 business days",
        "CREDIT_REPORTING": "30 days",
        "CUSTOMER_SERVICE": "5 business days",
    }
    return windows.get(issue_type, "30 calendar days")


def _assign_team(issue_type: str) -> str:
    teams = {
        "FRAUD": "Fraud & Security Operations",
        "BILLING": "Billing Resolution Team",
        "IDENTITY_THEFT": "Identity Protection Unit",
        "PAYMENT": "Payments Operations",
        "CREDIT_REPORTING": "Credit Bureau Relations",
        "CUSTOMER_SERVICE": "Customer Experience Escalations",
    }
    return teams.get(issue_type, "General Complaint Resolution")


def _mock_response_draft(
    issue_type: str,
    steps: List[RemediationStep],
    state_code: str,
) -> str:
    action_list = "\n".join(f"  {s.order}. {s.action}" for s in steps[:4])
    return f"""Dear Valued Customer,

Thank you for bringing this matter to our attention. We take all customer complaints
seriously and are committed to resolving your concern regarding your {issue_type.replace('_', ' ').title()}
issue promptly and in full compliance with applicable regulations.

SUMMARY OF YOUR CONCERN
We have reviewed your complaint and acknowledge the issue you have described. Our
investigation has been initiated and assigned to our {_assign_team(issue_type)}.

STEPS WE ARE TAKING
{action_list}

YOUR RIGHTS UNDER {_policy_ref(issue_type)}
You have the right to request documentation of our investigation findings. If you
are not satisfied with our resolution, you may file a complaint with the Consumer
Financial Protection Bureau (CFPB) at consumerfinance.gov/complaint or by calling
(855) 411-CFPB.

TIMELINE
We will complete our investigation and provide a written response within {_sla_window(issue_type)}.

If you have any questions, please contact our dedicated resolution line at 1-800-XXX-XXXX,
Monday–Friday, 8 AM–8 PM EST.

Sincerely,
FinComplaint AI Resolution Team
Case Reference: AUTO-GENERATED
State: {state_code}
"""


def _mock_explanation(
    classification: ClassificationResult,
    root_cause: str,
    audit_verdict: str,
) -> str:
    return (
        f"CLASSIFICATION RATIONALE\n"
        f"The complaint was classified as {classification.product_type} / {classification.issue_type} "
        f"with {classification.severity} severity and {classification.compliance_risk} compliance risk. "
        f"Confidence: {classification.confidence:.0%}. The classifier used keyword-weighted heuristics "
        f"combined with LLM structured output. Schema validation passed on first attempt.\n\n"
        f"ROOT CAUSE SUMMARY\n"
        f"{root_cause}\n\n"
        f"REMEDIATION JUSTIFICATION\n"
        f"The action plan was grounded in {_policy_ref(classification.issue_type)}. "
        f"Each step was verified against the MCP policy server's SLA requirements for "
        f"the {classification.issue_type} issue type.\n\n"
        f"AUDIT VERDICT: {audit_verdict}\n"
        f"The compliance auditor reviewed the response draft against CFPB guidelines. "
        f"{'No compliance issues were found.' if audit_verdict == 'PASS' else 'Minor issues were identified and corrected in a second pass.'}\n\n"
        f"PIPELINE INTEGRITY\n"
        f"All 8 pipeline nodes completed successfully. Audit trail written to database. "
        f"This explanation is suitable for regulatory review and CFPB submission."
    )
