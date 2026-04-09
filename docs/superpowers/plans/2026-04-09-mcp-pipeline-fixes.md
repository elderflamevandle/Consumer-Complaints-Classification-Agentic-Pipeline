# MCP Server & Pipeline Agentic Flow Fixes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 4 bugs: MCP issue-type key mismatch, relative server path, missing triage flag, and orphaned dead-code files.

**Architecture:** The MCP server's `_normalize_issue` is extended to strip punctuation so long CFPB display strings map cleanly to JSON keys. `mock_regulations.json` is expanded to cover all 40 issue types in 5 SLA buckets. `PipelineState` gains `triage_flag`/`triage_reason` fields set in `issue_classifier_node`. Four orphaned graph files and their tests are deleted.

**Tech Stack:** Python 3.11, Pydantic v2, LangGraph, pytest

---

## File Map

| File | Action | Reason |
|------|--------|--------|
| `mcp_server/server.py` | Modify | Strip punctuation from `_normalize_issue` |
| `mcp_server/mock_regulations.json` | Rewrite | Add entries for all 40 CFPB issue types |
| `src/tools/mcp_policy_client.py` | Modify | Fix relative → absolute server path |
| `src/graph/langgraph_state.py` | Modify | Add `triage_flag`, `triage_reason` fields |
| `src/graph/nodes.py` | Modify | Compute triage in `issue_classifier_node`; fix stale docstring |
| `src/graph/response_loop.py` | Delete | Orphaned — not called by LangGraph pipeline |
| `src/graph/routing.py` | Delete | Orphaned — not called by LangGraph pipeline |
| `src/graph/interrupts.py` | Delete | Orphaned — not called by LangGraph pipeline |
| `src/graph/state.py` | Delete | All exports only used by above 3 deleted files |
| `tests/test_routing_interrupts.py` | Delete | Imports deleted modules |
| `tests/test_phase4_state.py` | Delete | Imports deleted modules |
| `tests/test_remediator_mcp.py` | Modify | Update `_classification()` to use valid CFPB issue type |
| `tests/test_mcp_normalization.py` | Create | New: verify server normalization and regulation lookup |
| `tests/test_triage_flag.py` | Create | New: verify triage flag logic in issue_classifier_node |

---

## Task 1: Fix `_normalize_issue` in MCP server to strip punctuation

CFPB display strings contain apostrophes (e.g. `company's`) and commas (e.g. `marketing, including`). The current normalizer keeps those characters, making JSON key lookups fail. This task extends the normalizer to strip all non-alphanumeric, non-underscore characters.

**Files:**
- Modify: `mcp_server/server.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_mcp_normalization.py`:

```python
"""Tests for MCP server _normalize_issue function and expanded regulation lookups."""
from __future__ import annotations

from mcp_server.server import _normalize_issue, get_sla_requirements


def test_normalize_strips_apostrophe() -> None:
    result = _normalize_issue("Problem with a company's investigation into an existing problem")
    assert result == "PROBLEM_WITH_A_COMPANYS_INVESTIGATION_INTO_AN_EXISTING_PROBLEM"
    assert "'" not in result


def test_normalize_strips_comma() -> None:
    result = _normalize_issue("Advertising and marketing, including promotional offers")
    assert result == "ADVERTISING_AND_MARKETING_INCLUDING_PROMOTIONAL_OFFERS"
    assert "," not in result


def test_normalize_strips_comma_in_managing_opening() -> None:
    result = _normalize_issue("Managing, opening, or closing your mobile wallet account")
    assert result == "MANAGING_OPENING_OR_CLOSING_YOUR_MOBILE_WALLET_ACCOUNT"


def test_normalize_strips_comma_in_overdraft() -> None:
    result = _normalize_issue("Overdraft, savings, or rewards features")
    assert result == "OVERDRAFT_SAVINGS_OR_REWARDS_FEATURES"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd F:/Agentic_Hackathon && python -m pytest tests/test_mcp_normalization.py::test_normalize_strips_apostrophe tests/test_mcp_normalization.py::test_normalize_strips_comma -v
```

Expected: FAIL — apostrophe and comma still present in output.

- [ ] **Step 3: Implement the fix**

In `mcp_server/server.py`, add `import re` at the top and update `_normalize_issue`:

```python
import re  # add after existing imports

def _normalize_issue(issue_type: str) -> str:
    normalized = issue_type.strip().upper()
    normalized = re.sub(r'[\s\-]+', '_', normalized)   # spaces/hyphens → underscore
    normalized = re.sub(r'[^A-Z0-9_]', '', normalized) # remove all other non-word chars
    return normalized
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd F:/Agentic_Hackathon && python -m pytest tests/test_mcp_normalization.py::test_normalize_strips_apostrophe tests/test_mcp_normalization.py::test_normalize_strips_comma tests/test_mcp_normalization.py::test_normalize_strips_comma_in_managing_opening tests/test_mcp_normalization.py::test_normalize_strips_comma_in_overdraft -v
```

Expected: 4 PASS

- [ ] **Step 5: Commit**

```bash
git add mcp_server/server.py tests/test_mcp_normalization.py
git commit -m "fix(mcp): strip punctuation from issue-type normalizer"
```

---

## Task 2: Expand `mock_regulations.json` with all 40 CFPB issue types

The updated normalizer produces clean keys. This task adds entries for every CFPB issue type grouped into 5 SLA buckets: fraud (10 days), billing (21 days), credit reporting (30 days FCRA), debt collection (30 days FDCPA), and hardship (30 days). General/operational issues fall through to the existing `default` (30 days).

**Files:**
- Rewrite: `mcp_server/mock_regulations.json`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_mcp_normalization.py`:

```python
def test_fraud_issue_returns_10_day_sla() -> None:
    result = get_sla_requirements(issue_type="Fraud or scam", state_code="TX")
    assert result["sla_window"] == "10 calendar days"
    assert "FRAUD_OR_SCAM" == result["issue_type"]


def test_billing_issue_returns_21_day_sla() -> None:
    result = get_sla_requirements(issue_type="Fees or interest", state_code="TX")
    assert result["sla_window"] == "21 calendar days"


def test_credit_reporting_issue_returns_fcra_basis() -> None:
    result = get_sla_requirements(issue_type="Incorrect information on your report", state_code="TX")
    assert "FCRA" in result["regulatory_basis"]


def test_debt_collection_issue_returns_fdcpa_basis() -> None:
    result = get_sla_requirements(issue_type="Attempts to collect debt not owed", state_code="TX")
    assert "FDCPA" in result["regulatory_basis"]


def test_unauthorized_transactions_returns_fraud_sla() -> None:
    result = get_sla_requirements(
        issue_type="Unauthorized transactions or other transaction problem", state_code="TX"
    )
    assert result["sla_window"] == "10 calendar days"


def test_billing_ca_override_returns_15_day_sla() -> None:
    result = get_sla_requirements(issue_type="Fees or interest", state_code="CA")
    assert result["sla_window"] == "15 calendar days"


def test_fraud_ny_override_returns_7_day_sla() -> None:
    result = get_sla_requirements(issue_type="Fraud or scam", state_code="NY")
    assert result["sla_window"] == "7 calendar days"


def test_general_issue_returns_default_30_day_sla() -> None:
    result = get_sla_requirements(issue_type="Closing an account", state_code="TX")
    assert result["sla_window"] == "30 calendar days"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd F:/Agentic_Hackathon && python -m pytest tests/test_mcp_normalization.py -k "sla or basis or override" -v
```

Expected: FAIL — most issue types return the default 30-day policy.

- [ ] **Step 3: Rewrite `mock_regulations.json`**

Replace the entire file with:

```json
{
  "default": {
    "sla_window": "30 calendar days",
    "required_actions": [
      "Acknowledge complaint receipt",
      "Open internal case and assign owner",
      "Provide written resolution summary"
    ],
    "regulatory_basis": "CFPB complaint response baseline guidance"
  },
  "issues": {
    "FRAUD_OR_SCAM": {
      "default": {
        "sla_window": "10 calendar days",
        "required_actions": [
          "Lock compromised account access",
          "Start fraud investigation and document timeline",
          "Provide customer update every 3 business days"
        ],
        "regulatory_basis": "Electronic fund transfer fraud handling standards"
      },
      "states": {
        "NY": {
          "sla_window": "7 calendar days",
          "required_actions": [
            "Escalate suspected fraud to specialized response unit",
            "Issue temporary account protections and provisional credit",
            "Share written case status every 48 hours"
          ],
          "regulatory_basis": "NYDFS consumer fraud response expectations"
        }
      }
    },
    "UNAUTHORIZED_TRANSACTIONS_OR_OTHER_TRANSACTION_PROBLEM": {
      "default": {
        "sla_window": "10 calendar days",
        "required_actions": [
          "Lock compromised account access",
          "Start fraud investigation and document timeline",
          "Provide customer update every 3 business days"
        ],
        "regulatory_basis": "Electronic fund transfer fraud handling standards"
      },
      "states": {
        "NY": {
          "sla_window": "7 calendar days",
          "required_actions": [
            "Escalate to specialized fraud response unit",
            "Issue provisional credit within 2 business days",
            "Share written status every 48 hours"
          ],
          "regulatory_basis": "NYDFS consumer fraud response expectations"
        }
      }
    },
    "PROBLEM_WITH_FRAUD_ALERTS_OR_SECURITY_FREEZES": {
      "default": {
        "sla_window": "10 calendar days",
        "required_actions": [
          "Acknowledge the fraud alert or freeze request",
          "Verify identity before modifying security settings",
          "Confirm placement or removal in writing"
        ],
        "regulatory_basis": "Electronic fund transfer fraud handling standards"
      }
    },
    "IDENTITY_THEFT_PROTECTION_OR_OTHER_MONITORING_SERVICES": {
      "default": {
        "sla_window": "10 calendar days",
        "required_actions": [
          "Suspend suspected unauthorized service enrollment",
          "Conduct identity verification review",
          "Provide written findings and next steps"
        ],
        "regulatory_basis": "Electronic fund transfer fraud handling standards"
      }
    },
    "CREDIT_MONITORING_OR_IDENTITY_THEFT_PROTECTION_SERVICES": {
      "default": {
        "sla_window": "10 calendar days",
        "required_actions": [
          "Suspend suspected unauthorized service enrollment",
          "Conduct identity verification review",
          "Provide written findings and next steps"
        ],
        "regulatory_basis": "Electronic fund transfer fraud handling standards"
      }
    },
    "FEES_OR_INTEREST": {
      "default": {
        "sla_window": "21 calendar days",
        "required_actions": [
          "Validate disputed fee or interest charge",
          "Suspend related late fees while investigation is active",
          "Provide written investigation findings"
        ],
        "regulatory_basis": "Regulation Z billing error framework"
      },
      "states": {
        "CA": {
          "sla_window": "15 calendar days",
          "required_actions": [
            "Acknowledge complaint within 2 business days",
            "Validate disputed charge and merchant evidence",
            "Issue provisional credit if investigation exceeds 10 days"
          ],
          "regulatory_basis": "CA consumer financial complaint timing guidance"
        }
      }
    },
    "PROBLEM_WITH_A_PURCHASE_SHOWN_ON_YOUR_STATEMENT": {
      "default": {
        "sla_window": "21 calendar days",
        "required_actions": [
          "Validate disputed transaction details",
          "Suspend late fees while investigation is active",
          "Provide written investigation findings"
        ],
        "regulatory_basis": "Regulation Z billing error framework"
      },
      "states": {
        "CA": {
          "sla_window": "15 calendar days",
          "required_actions": [
            "Acknowledge complaint within 2 business days",
            "Validate disputed charge and merchant evidence",
            "Issue provisional credit if investigation exceeds 10 days"
          ],
          "regulatory_basis": "CA consumer financial complaint timing guidance"
        }
      }
    },
    "PROBLEM_WHEN_MAKING_PAYMENTS": {
      "default": {
        "sla_window": "21 calendar days",
        "required_actions": [
          "Identify root cause of payment processing failure",
          "Waive penalty fees incurred during processing error",
          "Confirm corrected payment processing in writing"
        ],
        "regulatory_basis": "Regulation Z billing error framework"
      }
    },
    "PROBLEM_WITH_A_LENDER_OR_OTHER_COMPANY_CHARGING_YOUR_ACCOUNT": {
      "default": {
        "sla_window": "21 calendar days",
        "required_actions": [
          "Validate authorization for the disputed charge",
          "Suspend further charges pending investigation",
          "Provide written investigation findings"
        ],
        "regulatory_basis": "Regulation Z billing error framework"
      },
      "states": {
        "CA": {
          "sla_window": "15 calendar days",
          "required_actions": [
            "Acknowledge complaint within 2 business days",
            "Validate disputed charge and merchant evidence",
            "Issue provisional credit if investigation exceeds 10 days"
          ],
          "regulatory_basis": "CA consumer financial complaint timing guidance"
        }
      }
    },
    "UNEXPECTED_OR_OTHER_FEES": {
      "default": {
        "sla_window": "21 calendar days",
        "required_actions": [
          "Validate whether fee was disclosed at account opening",
          "Reverse undisclosed or erroneous fees",
          "Provide written summary of fee review outcome"
        ],
        "regulatory_basis": "Regulation Z billing error framework"
      }
    },
    "WRONG_AMOUNT_CHARGED_OR_RECEIVED": {
      "default": {
        "sla_window": "21 calendar days",
        "required_actions": [
          "Verify transaction amount against merchant record",
          "Issue correction or provisional credit",
          "Confirm corrected amount in writing"
        ],
        "regulatory_basis": "Regulation Z billing error framework"
      }
    },
    "PROBLEM_CAUSED_BY_YOUR_FUNDS_BEING_LOW": {
      "default": {
        "sla_window": "21 calendar days",
        "required_actions": [
          "Review overdraft and NSF fee assessment",
          "Waive fees caused by erroneous low-balance triggers",
          "Provide written summary and corrective actions"
        ],
        "regulatory_basis": "Regulation Z billing error framework"
      }
    },
    "INCORRECT_EXCHANGE_RATE": {
      "default": {
        "sla_window": "21 calendar days",
        "required_actions": [
          "Verify exchange rate applied against market rate on transaction date",
          "Calculate and refund any exchange rate overcharge",
          "Provide written adjustment summary"
        ],
        "regulatory_basis": "Regulation Z billing error framework"
      }
    },
    "OVERDRAFT_SAVINGS_OR_REWARDS_FEATURES": {
      "default": {
        "sla_window": "21 calendar days",
        "required_actions": [
          "Review overdraft or rewards program terms as applied",
          "Reverse incorrectly assessed overdraft fees",
          "Provide written findings and corrective actions"
        ],
        "regulatory_basis": "Regulation Z billing error framework"
      }
    },
    "INCORRECT_INFORMATION_ON_YOUR_REPORT": {
      "default": {
        "sla_window": "30 calendar days",
        "required_actions": [
          "Initiate FCRA dispute investigation with furnisher",
          "Provide consumer written notification of investigation status",
          "Correct or delete inaccurate information within statutory timeframe"
        ],
        "regulatory_basis": "FCRA dispute investigation requirements"
      }
    },
    "IMPROPER_USE_OF_YOUR_REPORT": {
      "default": {
        "sla_window": "30 calendar days",
        "required_actions": [
          "Verify permissible purpose for the credit report access",
          "Remove unauthorized inquiry if no permissible purpose exists",
          "Provide consumer with written outcome"
        ],
        "regulatory_basis": "FCRA dispute investigation requirements"
      }
    },
    "PROBLEM_WITH_A_COMPANYS_INVESTIGATION_INTO_AN_EXISTING_PROBLEM": {
      "default": {
        "sla_window": "30 calendar days",
        "required_actions": [
          "Reopen investigation with additional supporting documentation",
          "Notify consumer of reinvestigation status within 5 business days",
          "Provide written final determination"
        ],
        "regulatory_basis": "FCRA dispute investigation requirements"
      }
    },
    "PROBLEM_WITH_A_COMPANYS_INVESTIGATION_INTO_AN_EXISTING_ISSUE": {
      "default": {
        "sla_window": "30 calendar days",
        "required_actions": [
          "Reopen investigation with additional supporting documentation",
          "Notify consumer of reinvestigation status within 5 business days",
          "Provide written final determination"
        ],
        "regulatory_basis": "FCRA dispute investigation requirements"
      }
    },
    "UNABLE_TO_GET_YOUR_CREDIT_REPORT_OR_CREDIT_SCORE": {
      "default": {
        "sla_window": "30 calendar days",
        "required_actions": [
          "Investigate reason for access failure",
          "Remove any erroneous block on report access",
          "Confirm restored access in writing to consumer"
        ],
        "regulatory_basis": "FCRA dispute investigation requirements"
      }
    },
    "ATTEMPTS_TO_COLLECT_DEBT_NOT_OWED": {
      "default": {
        "sla_window": "30 calendar days",
        "required_actions": [
          "Verify debt validity and ownership documentation",
          "Cease collection activity if debt cannot be validated",
          "Provide consumer written validation notice within 5 days"
        ],
        "regulatory_basis": "FDCPA consumer protection standards"
      }
    },
    "COMMUNICATION_TACTICS": {
      "default": {
        "sla_window": "30 calendar days",
        "required_actions": [
          "Review communication logs for FDCPA compliance",
          "Cease prohibited communication practices immediately",
          "Provide written acknowledgment of complaint and corrective action"
        ],
        "regulatory_basis": "FDCPA consumer protection standards"
      }
    },
    "ELECTRONIC_COMMUNICATIONS": {
      "default": {
        "sla_window": "30 calendar days",
        "required_actions": [
          "Verify consumer consent for electronic contact method",
          "Cease non-consented electronic communications",
          "Confirm corrective action in writing"
        ],
        "regulatory_basis": "FDCPA consumer protection standards"
      }
    },
    "FALSE_STATEMENTS_OR_REPRESENTATION": {
      "default": {
        "sla_window": "30 calendar days",
        "required_actions": [
          "Investigate accuracy of statements made to consumer",
          "Issue written correction for any false representation",
          "Retrain or escalate responsible collector"
        ],
        "regulatory_basis": "FDCPA consumer protection standards"
      }
    },
    "THREATENED_TO_CONTACT_SOMEONE_OR_SHARE_INFORMATION_IMPROPERLY": {
      "default": {
        "sla_window": "30 calendar days",
        "required_actions": [
          "Review communication records for prohibited third-party disclosures",
          "Issue cease-and-desist on improper contact",
          "Provide consumer written confirmation of corrective action"
        ],
        "regulatory_basis": "FDCPA consumer protection standards"
      }
    },
    "TOOK_OR_THREATENED_TO_TAKE_NEGATIVE_OR_LEGAL_ACTION": {
      "default": {
        "sla_window": "30 calendar days",
        "required_actions": [
          "Verify legal authority to take threatened action",
          "Withdraw unlawful threats in writing",
          "Document corrective action in consumer file"
        ],
        "regulatory_basis": "FDCPA consumer protection standards"
      }
    },
    "WRITTEN_NOTIFICATION_ABOUT_DEBT": {
      "default": {
        "sla_window": "30 calendar days",
        "required_actions": [
          "Verify required debt validation notice was provided",
          "Issue corrected written notice if original was deficient",
          "Confirm consumer receipt of corrected notice"
        ],
        "regulatory_basis": "FDCPA consumer protection standards"
      }
    },
    "STRUGGLING_TO_PAY_YOUR_BILL": {
      "default": {
        "sla_window": "30 calendar days",
        "required_actions": [
          "Review available hardship or payment plan options",
          "Suspend adverse actions while hardship request is evaluated",
          "Provide written decision on hardship assistance"
        ],
        "regulatory_basis": "CFPB loss mitigation and hardship guidelines"
      }
    },
    "STRUGGLING_TO_PAY_MORTGAGE": {
      "default": {
        "sla_window": "30 calendar days",
        "required_actions": [
          "Acknowledge loss mitigation application receipt",
          "Assign dedicated loss mitigation specialist",
          "Provide written decision within regulatory timeframe"
        ],
        "regulatory_basis": "CFPB loss mitigation and hardship guidelines"
      }
    },
    "STRUGGLING_TO_PAY_YOUR_LOAN": {
      "default": {
        "sla_window": "30 calendar days",
        "required_actions": [
          "Review loan modification or deferral options",
          "Suspend repossession proceedings while review is active",
          "Provide written decision on assistance options"
        ],
        "regulatory_basis": "CFPB loss mitigation and hardship guidelines"
      }
    },
    "TROUBLE_DURING_PAYMENT_PROCESS": {
      "default": {
        "sla_window": "30 calendar days",
        "required_actions": [
          "Identify root cause of payment processing issue",
          "Waive fees caused by servicer error",
          "Confirm corrected payment application in writing"
        ],
        "regulatory_basis": "CFPB loss mitigation and hardship guidelines"
      }
    },
    "APPLYING_FOR_A_MORTGAGE_OR_REFINANCING_AN_EXISTING_MORTGAGE": {
      "default": {
        "sla_window": "30 calendar days",
        "required_actions": [
          "Review application for discriminatory or procedural errors",
          "Provide written adverse action notice if applicable",
          "Document corrective actions in consumer file"
        ],
        "regulatory_basis": "CFPB loss mitigation and hardship guidelines"
      }
    },
    "CLOSING_ON_A_MORTGAGE": {
      "default": {
        "sla_window": "30 calendar days",
        "required_actions": [
          "Identify cause of closing delay or dispute",
          "Provide corrected closing disclosure if required",
          "Confirm resolution in writing to consumer"
        ],
        "regulatory_basis": "CFPB loss mitigation and hardship guidelines"
      }
    },
    "REPOSSESSION": {
      "default": {
        "sla_window": "30 calendar days",
        "required_actions": [
          "Verify repossession was conducted within legal authority",
          "Review reinstatement or redemption options",
          "Provide consumer written summary of rights and options"
        ],
        "regulatory_basis": "CFPB loss mitigation and hardship guidelines"
      }
    },
    "PROBLEMS_AT_THE_END_OF_THE_LOAN_OR_LEASE": {
      "default": {
        "sla_window": "30 calendar days",
        "required_actions": [
          "Verify accuracy of end-of-term charges or residual calculation",
          "Waive erroneous end-of-term fees",
          "Provide written resolution summary"
        ],
        "regulatory_basis": "CFPB loss mitigation and hardship guidelines"
      }
    }
  }
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd F:/Agentic_Hackathon && python -m pytest tests/test_mcp_normalization.py -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add mcp_server/mock_regulations.json tests/test_mcp_normalization.py
git commit -m "feat(mcp): expand regulations to cover all 40 CFPB issue types"
```

---

## Task 3: Fix MCP client server path (relative → absolute)

`DEFAULT_SERVER_PATH = Path('mcp_server/server.py')` breaks when the process CWD is not the project root. Anchoring to `__file__` makes it CWD-independent.

**Files:**
- Modify: `src/tools/mcp_policy_client.py` (line 15)

- [ ] **Step 1: Write the failing test**

Add to `tests/test_mcp_normalization.py`:

```python
from src.tools.mcp_policy_client import MCPPolicyClient


def test_default_server_path_is_absolute_and_exists() -> None:
    client = MCPPolicyClient()
    assert client.server_path.is_absolute(), "server_path must be absolute"
    assert client.server_path.exists(), f"server not found at {client.server_path}"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd F:/Agentic_Hackathon && python -m pytest tests/test_mcp_normalization.py::test_default_server_path_is_absolute_and_exists -v
```

Expected: FAIL — path is relative, `is_absolute()` returns False.

- [ ] **Step 3: Implement the fix**

In `src/tools/mcp_policy_client.py`, replace line 15:

```python
# Before
DEFAULT_SERVER_PATH = Path('mcp_server/server.py')

# After
DEFAULT_SERVER_PATH = Path(__file__).parent.parent.parent / 'mcp_server' / 'server.py'
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd F:/Agentic_Hackathon && python -m pytest tests/test_mcp_normalization.py::test_default_server_path_is_absolute_and_exists -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/tools/mcp_policy_client.py tests/test_mcp_normalization.py
git commit -m "fix(mcp): anchor server path to file location instead of CWD"
```

---

## Task 4: Add triage fields to PipelineState and compute them

Adds `triage_flag: bool` and `triage_reason: str` to `PipelineState`. Computes them in `issue_classifier_node` immediately after classification. A complaint is flagged when: confidence < 0.70, compliance_risk is HIGH, or severity is CRITICAL.

**Files:**
- Modify: `src/graph/langgraph_state.py`
- Modify: `src/graph/nodes.py`
- Create: `tests/test_triage_flag.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_triage_flag.py`:

```python
"""Tests for triage flag computation in the issue_classifier_node."""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from src.graph.nodes import issue_classifier_node
from src.schemas.classification import (
    ComplianceRisk,
    IssueClassificationResult,
    IssueType,
    ProductClassificationResult,
    ProductType,
    SeverityLevel,
)
from src.schemas.intake import IntakePreparation


def _make_state(
    issue: IssueType = IssueType.FEES_OR_INTEREST,
    severity: SeverityLevel = SeverityLevel.LOW,
    compliance_risk: ComplianceRisk = ComplianceRisk.LOW,
    confidence: float = 0.90,
) -> dict[str, Any]:
    intake = MagicMock(spec=IntakePreparation)
    intake.scrubbed_text = "test complaint"
    product_result = MagicMock(spec=ProductClassificationResult)
    product_result.product = ProductType.CREDIT_CARD
    return {
        "thread_id": "thread-test",
        "intake": intake,
        "product_classification": product_result,
    }


def _make_issue_result(
    issue: IssueType = IssueType.FEES_OR_INTEREST,
    severity: SeverityLevel = SeverityLevel.LOW,
    compliance_risk: ComplianceRisk = ComplianceRisk.LOW,
    confidence: float = 0.90,
) -> IssueClassificationResult:
    result = MagicMock(spec=IssueClassificationResult)
    result.issue = issue
    result.severity = severity
    result.compliance_risk = compliance_risk
    result.confidence = confidence
    merged = MagicMock()
    merged.issue_type = issue
    result.to_classification_result.return_value = merged
    return result


def test_no_triage_flag_for_normal_complaint() -> None:
    state = _make_state()
    issue_result = _make_issue_result(
        severity=SeverityLevel.LOW,
        compliance_risk=ComplianceRisk.LOW,
        confidence=0.90,
    )
    with patch(
        "src.graph.nodes._get_issue_classifier"
    ) as mock_cls:
        mock_cls.return_value.classify_issue.return_value = issue_result
        mock_cls.return_value.last_model = "test-model"
        result = issue_classifier_node(state)

    assert result["triage_flag"] is False
    assert result["triage_reason"] == ""


def test_triage_flag_set_for_critical_severity() -> None:
    state = _make_state()
    issue_result = _make_issue_result(
        severity=SeverityLevel.CRITICAL,
        compliance_risk=ComplianceRisk.LOW,
        confidence=0.90,
    )
    with patch(
        "src.graph.nodes._get_issue_classifier"
    ) as mock_cls:
        mock_cls.return_value.classify_issue.return_value = issue_result
        mock_cls.return_value.last_model = "test-model"
        result = issue_classifier_node(state)

    assert result["triage_flag"] is True
    assert "critical_severity" in result["triage_reason"]


def test_triage_flag_set_for_high_compliance_risk() -> None:
    state = _make_state()
    issue_result = _make_issue_result(
        severity=SeverityLevel.MEDIUM,
        compliance_risk=ComplianceRisk.HIGH,
        confidence=0.90,
    )
    with patch(
        "src.graph.nodes._get_issue_classifier"
    ) as mock_cls:
        mock_cls.return_value.classify_issue.return_value = issue_result
        mock_cls.return_value.last_model = "test-model"
        result = issue_classifier_node(state)

    assert result["triage_flag"] is True
    assert "high_compliance_risk" in result["triage_reason"]


def test_triage_flag_set_for_low_confidence() -> None:
    state = _make_state()
    issue_result = _make_issue_result(
        severity=SeverityLevel.LOW,
        compliance_risk=ComplianceRisk.LOW,
        confidence=0.65,
    )
    with patch(
        "src.graph.nodes._get_issue_classifier"
    ) as mock_cls:
        mock_cls.return_value.classify_issue.return_value = issue_result
        mock_cls.return_value.last_model = "test-model"
        result = issue_classifier_node(state)

    assert result["triage_flag"] is True
    assert "low_confidence" in result["triage_reason"]


def test_triage_reason_combines_multiple_triggers() -> None:
    state = _make_state()
    issue_result = _make_issue_result(
        severity=SeverityLevel.CRITICAL,
        compliance_risk=ComplianceRisk.HIGH,
        confidence=0.60,
    )
    with patch(
        "src.graph.nodes._get_issue_classifier"
    ) as mock_cls:
        mock_cls.return_value.classify_issue.return_value = issue_result
        mock_cls.return_value.last_model = "test-model"
        result = issue_classifier_node(state)

    assert result["triage_flag"] is True
    assert "low_confidence" in result["triage_reason"]
    assert "high_compliance_risk" in result["triage_reason"]
    assert "critical_severity" in result["triage_reason"]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd F:/Agentic_Hackathon && python -m pytest tests/test_triage_flag.py -v
```

Expected: FAIL — `triage_flag` key not found in result dict.

- [ ] **Step 3: Add fields to PipelineState**

In `src/graph/langgraph_state.py`, add two fields after `# --- Error handling ---`:

```python
    # --- Triage ---
    triage_flag: bool                    # True when complaint needs elevated handling
    triage_reason: str                   # e.g. "high_compliance_risk,critical_severity"

    # --- Error handling ---
    error: str
```

- [ ] **Step 4: Add triage computation to `issue_classifier_node`**

In `src/graph/nodes.py`:

1. Update the docstring at the top of the file — change the stale comment block (lines 9-13):

```python
"""LangGraph node functions for the FinComplaint AI multi-agent pipeline.

Each node function:
  - Accepts PipelineState
  - Returns dict[str, Any] with only the keys it modifies
  - Wraps an existing agent or service from src/agents/ or src/tools/

Node execution order (defined in pipeline.py):
  intake → product_classifier → issue_classifier → root_cause
    → remediator → response_writer → response_auditor
    → [loop back to response_writer if needs_rewrite]
    → explainer → END
"""
```

2. Add the missing imports at the top of the file (after the existing imports):

```python
from src.schemas.classification import ComplianceRisk, ProductType, SeverityLevel
```

3. Replace the `issue_classifier_node` return block (after `combined = issue_result.to_classification_result(product_result.product)`) with:

```python
    # Compute triage flag
    triage_reasons: list[str] = []
    if issue_result.confidence < 0.70:
        triage_reasons.append("low_confidence")
    if issue_result.compliance_risk == ComplianceRisk.HIGH:
        triage_reasons.append("high_compliance_risk")
    if issue_result.severity == SeverityLevel.CRITICAL:
        triage_reasons.append("critical_severity")
    triage_flag = len(triage_reasons) > 0
    triage_reason = ",".join(triage_reasons)

    return {
        'issue_classification': issue_result,
        'classification': combined,
        'triage_flag': triage_flag,
        'triage_reason': triage_reason,
        'events': [
            f'{thread_id}:issue_classified:{issue_result.issue.value}',
            f'{thread_id}:severity:{issue_result.severity.value}',
        ],
        'stage_telemetry': [
            _telemetry('issue_classifier', latency, model=agent.last_model or 'unknown')
        ],
    }
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd F:/Agentic_Hackathon && python -m pytest tests/test_triage_flag.py -v
```

Expected: 5 PASS

- [ ] **Step 6: Commit**

```bash
git add src/graph/langgraph_state.py src/graph/nodes.py tests/test_triage_flag.py
git commit -m "feat(pipeline): add triage_flag and triage_reason to PipelineState"
```

---

## Task 5: Delete orphaned graph files and their tests

Four graph files (`response_loop.py`, `routing.py`, `interrupts.py`, `state.py`) and two test files (`test_routing_interrupts.py`, `test_phase4_state.py`) are dead code from before the HITL removal. Deleting them removes confusion and import errors.

**Files:**
- Delete: `src/graph/response_loop.py`
- Delete: `src/graph/routing.py`
- Delete: `src/graph/interrupts.py`
- Delete: `src/graph/state.py`
- Delete: `tests/test_routing_interrupts.py`
- Delete: `tests/test_phase4_state.py`

- [ ] **Step 1: Verify nothing in the live pipeline imports these files**

```bash
cd F:/Agentic_Hackathon && grep -rn "from src.graph.response_loop\|from src.graph.routing\|from src.graph.interrupts\|from src.graph.state" src/ --include="*.py"
```

Expected: zero matches (only the files themselves and tests should appear if any).

- [ ] **Step 2: Delete the orphaned source files**

```bash
rm "F:/Agentic_Hackathon/src/graph/response_loop.py"
rm "F:/Agentic_Hackathon/src/graph/routing.py"
rm "F:/Agentic_Hackathon/src/graph/interrupts.py"
rm "F:/Agentic_Hackathon/src/graph/state.py"
```

- [ ] **Step 3: Delete the orphaned test files**

```bash
rm "F:/Agentic_Hackathon/tests/test_routing_interrupts.py"
rm "F:/Agentic_Hackathon/tests/test_phase4_state.py"
```

- [ ] **Step 4: Verify test suite still collects without import errors**

```bash
cd F:/Agentic_Hackathon && python -m pytest --collect-only 2>&1 | grep -E "ERROR|error" | head -20
```

Expected: no import errors.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "chore: delete orphaned HITL graph files and their tests"
```

---

## Task 6: Fix `test_remediator_mcp.py` — update to valid CFPB issue type

`test_remediator_mcp.py` uses `issue_type='BILLING'` which is a legacy short code that no longer exists in `IssueType`. This causes a Pydantic `ValidationError`. Update the helper to use `IssueType.FEES_OR_INTEREST` (value: `"Fees or interest"`).

**Files:**
- Modify: `tests/test_remediator_mcp.py`

- [ ] **Step 1: Run existing test to confirm it is broken**

```bash
cd F:/Agentic_Hackathon && python -m pytest tests/test_remediator_mcp.py -v
```

Expected: FAIL — `ValidationError` for invalid IssueType `'BILLING'`.

- [ ] **Step 2: Fix `_classification()` helper**

In `tests/test_remediator_mcp.py`, replace the `_classification()` function:

```python
def _classification() -> ClassificationResult:
    return ClassificationResult(
        product_type='CREDIT_CARD',
        issue_type='Fees or interest',   # valid CFPB display string for IssueType.FEES_OR_INTEREST
        severity='HIGH',
        compliance_risk='HIGH',
        confidence=0.82,
    )
```

- [ ] **Step 3: Run tests to verify they pass**

```bash
cd F:/Agentic_Hackathon && python -m pytest tests/test_remediator_mcp.py -v
```

Expected: 3 PASS

- [ ] **Step 4: Run full test suite**

```bash
cd F:/Agentic_Hackathon && python -m pytest -q 2>&1 | tail -20
```

Expected: no failures related to this change.

- [ ] **Step 5: Commit**

```bash
git add tests/test_remediator_mcp.py
git commit -m "fix(tests): update remediator test to use valid CFPB issue type"
```

---

## Final Verification

- [ ] **Run full test suite**

```bash
cd F:/Agentic_Hackathon && python -m pytest -v 2>&1 | tail -40
```

Expected: all tests pass, no import errors.

- [ ] **Verify pipeline compiles end-to-end**

```bash
cd F:/Agentic_Hackathon && python -c "
from src.graph.pipeline import build_graph, run_complaint
g = build_graph()
print('Graph compiled OK:', type(g).__name__)
print('Nodes:', list(g.get_graph().nodes.keys()))
"
```

Expected:
```
Graph compiled OK: CompiledStateGraph
Nodes: ['__start__', 'intake_processor', 'product_classifier', 'issue_classifier', 'root_cause', 'remediator', 'response_writer', 'response_auditor', 'explainer', '__end__']
```

- [ ] **Verify MCP server round-trip for a fraud complaint**

```bash
cd F:/Agentic_Hackathon && python -c "
from mcp_server.server import get_sla_requirements
r = get_sla_requirements(issue_type='Fraud or scam', state_code='NY')
print('SLA:', r['sla_window'])
print('Basis:', r['regulatory_basis'])
"
```

Expected:
```
SLA: 7 calendar days
Basis: NYDFS consumer fraud response expectations
```
