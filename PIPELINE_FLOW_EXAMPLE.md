# FinComplaint AI Pipeline Flow With Example

## Overview

This document explains how the current backend pipeline processes one complaint from raw input to final output.

The flow is:

1. Intake preprocessing
2. Classification
3. Routing / human review gate
4. Root-cause diagnosis
5. Remediation planning with MCP policy lookup
6. Writer and auditor response loop
7. Explanation generation

## Stage-by-Stage Flow

### 1. Intake Preprocessing

File: `src/intake/pipeline.py`

What happens:

- Raw complaint text enters `prepare_intake(...)`
- PII scrubbing runs first
- Optional receipt text is appended for classifier context
- The system creates an `IntakePreparation` object

Important detail:

- The classifier receives `classifier_input_text`
- Downstream stages usually use `scrubbed_text`

### 2. Classification

File: `src/agents/classifier.py`

What happens:

- The classifier tries to return strict JSON with:
  - `product_type`
  - `issue_type`
  - `severity`
  - `compliance_risk`
  - `confidence`
- If the LLM output is invalid, the code retries
- If it still fails, it falls back to deterministic keyword heuristics

### 3. Routing / Human Review Gate

File: `src/graph/routing.py`

What happens:

- The routing layer decides whether the case can continue automatically
- It routes to human review when any of these are true:
  - confidence `< 0.70`
  - compliance risk is `HIGH`
  - severity is `CRITICAL`

If review is required, the case pauses until a reviewer:

- approves
- edits the classification
- rejects the case

### 4. Root-Cause Diagnosis

File: `src/agents/root_cause.py`

What happens:

- The system retrieves similar historical complaints from the local vector index
- It generates a structured root-cause result
- The output includes ranked evidence and citations

### 5. Remediation Planning

Files:

- `src/agents/remediator.py`
- `src/tools/mcp_policy_client.py`
- `mcp_server/server.py`

What happens:

- Before making an action plan, the pipeline queries the local MCP policy server
- The policy server returns state-specific SLA and required actions
- The remediator then creates a policy-grounded action plan

If policy lookup fails:

- the system returns `POLICY_UNAVAILABLE`
- the route becomes `human_review`

### 6. Response Writer + Auditor Loop

Files:

- `src/graph/response_loop.py`
- `src/agents/writer.py`
- `src/agents/auditor.py`

What happens:

- The writer creates a structured customer response
- The auditor checks for:
  - missing policy labels
  - overcommitment
  - unsafe tone
  - weak structure
  - unclear resolution
- If audit fails, the response is rewritten
- If the rewrite cap is reached, the pipeline escalates to human review

### 7. Explanation Generation

File: `src/agents/explainer.py`

What happens:

- After a final response is approved, the explainer summarizes the decision chain
- This explanation is for internal transparency and auditability

## One Concrete Example

### Raw Input

```text
My name is Mr. John. Someone committed fraud and identity theft, opened a checking account, and made an unauthorized transfer from my real bank account. SSN 111-22-3333. Call me at 555-123-4567.
```

### Receipt Context

```text
Dispute ref 88421. Temporary hold amount $950.00.
```

## How The Input Changes Through The Pipeline

### A. After Intake Preprocessing

```json
{
  "scrubbed_text": "My name is Mr. John. Someone committed fraud and identity theft, opened a checking account, and made an unauthorized transfer from my real bank account. SSN [SSN]. Call me at [PHONE].",
  "classifier_input_text": "My name is Mr. John. Someone committed fraud and identity theft, opened a checking account, and made an unauthorized transfer from my real bank account. SSN [SSN]. Call me at [PHONE].\n\n[RECEIPT_CONTEXT]\nDispute ref 88421. Temporary hold amount $950.00.",
  "scrub_confidence": 0.95,
  "review_policy": "auto",
  "receipt_attached": true
}
```

Notes:

- SSN changed to `[SSN]`
- phone number changed to `[PHONE]`
- receipt text was appended under `[RECEIPT_CONTEXT]`
- `Mr. John` was not redacted in this example because the current name-prefix regex is case-sensitive

### B. After Classification

```json
{
  "product_type": "BANK_ACCOUNT",
  "issue_type": "FRAUD",
  "severity": "CRITICAL",
  "compliance_risk": "HIGH",
  "confidence": 0.88
}
```

Interpretation:

- product is recognized as `BANK_ACCOUNT`
- complaint is classified as `FRAUD`
- severity is `CRITICAL`
- risk is `HIGH`

### C. After Routing

```json
{
  "route_before_review": "human_review",
  "review_required_before_review": true
}
```

Why:

- severity is `CRITICAL`
- compliance risk is `HIGH`

### D. After Human Review

In this walkthrough, the reviewer approves the case to continue:

```json
{
  "review_action": "approve",
  "route_after_review": "continue"
}
```

### E. After Root-Cause Diagnosis

```json
{
  "root_cause": "Likely account takeover triggered by identity theft, followed by unauthorized transfer activity and delayed fraud-case updates.",
  "evidence": [
    {
      "rank": 1,
      "citation": {
        "id": "CFPB-1001",
        "product": "bank_account",
        "issue": "fraud",
        "date": "2025-02-14"
      },
      "score": 0.93
    },
    {
      "rank": 2,
      "citation": {
        "id": "CFPB-1002",
        "product": "bank_account",
        "issue": "fraud",
        "date": "2025-01-30"
      },
      "score": 0.88
    }
  ],
  "ambiguity_flag": "CLEAR"
}
```

Interpretation:

- the system found similar historical fraud complaints
- it concluded the likely pattern is account takeover after identity theft
- the diagnosis is evidence-backed, not just free text

### F. After Remediation Planning

The system looks up NY fraud policy and produces:

```json
{
  "status": "ok",
  "route": "continue",
  "action_plan": [
    {
      "order": 1,
      "action": "Escalate the case to the specialized fraud response unit.",
      "policy_reference": "NYDFS consumer fraud response expectations"
    },
    {
      "order": 2,
      "action": "Apply temporary account protections and provisional credit while the review is active.",
      "policy_reference": "NYDFS consumer fraud response expectations"
    },
    {
      "order": 3,
      "action": "Send written status updates every 48 hours until the case is resolved.",
      "policy_reference": "NYDFS consumer fraud response expectations"
    }
  ],
  "policy_citations": {
    "sla_window": "7 calendar days",
    "required_actions": [
      "Escalate suspected fraud to specialized response unit",
      "Issue temporary account protections and provisional credit",
      "Share written case status every 48 hours"
    ],
    "regulatory_basis": "NYDFS consumer fraud response expectations"
  }
}
```

Interpretation:

- the action plan is grounded in policy
- the final response must respect the 7-day SLA and the NYDFS basis

### G. Response Writer + Auditor Loop

The first draft fails audit because the resolution was too weak.

```json
{
  "cycle_1": {
    "verdict": "FAIL",
    "fail_codes": ["UNCLEAR_RESOLUTION"]
  }
}
```

The second draft passes:

```json
{
  "cycle_2": {
    "verdict": "PASS",
    "fail_codes": []
  },
  "rewrite_count": 1,
  "response_loop_status": "approved"
}
```

## Final Output We Will Be Seeing

This is the final rendered customer-facing response:

```text
Acknowledgment:
We understand the urgency of the fraud and identity-theft concern you reported.

Findings:
We will investigate the suspected fraud, secure the affected account, and keep you informed under the required response timeline.
Current findings indicate suspected account takeover affecting a checking account, with historical patterns matching unauthorized transfer activity after identity theft.
Policy Labels: SLA window: 7 calendar days; Regulatory basis: NYDFS consumer fraud response expectations
Addressed Critiques: State the resolution path clearly in the findings block.

Action Steps:
1. Escalate the case to the specialized fraud response unit.
2. Apply temporary account protections and provisional credit while the review is active.
3. Send written status updates every 48 hours until the case is resolved.

Timeline / Next Steps:
We will continue providing written status updates within the 7 calendar day response window.
```

## Internal Explanation Output

After the customer response is approved, the explainer produces an internal summary like this:

```text
- [classification] Classified the complaint as BANK_ACCOUNT / FRAUD with confidence 0.88.
- [diagnosis] Diagnosis identified Likely account takeover triggered by identity theft, followed by unauthorized transfer activity and delayed fraud-case updates. (CFPB-1001:fraud, CFPB-1002:fraud)
- [remediation] Remediation produced 3 ordered action steps under NYDFS consumer fraud response expectations. (NYDFS consumer fraud response expectations)
- [response] Final response states: We will investigate the suspected fraud, secure the affected account, and keep you informed under the required response timeline. It preserves the four-block customer format. (SLA window: 7 calendar days, Regulatory basis: NYDFS consumer fraud response expectations)
- [audit] Audit verdict was PASS with 0 outstanding reason codes.
```

## Short Summary

In simple terms:

- raw complaint comes in
- PII is scrubbed
- complaint is classified
- risky cases are paused for review
- similar historical complaints are retrieved
- policy is fetched from MCP
- a response is written and audited
- the final customer response and internal explanation are produced

That is the end-to-end pipeline for the current backend implementation.
