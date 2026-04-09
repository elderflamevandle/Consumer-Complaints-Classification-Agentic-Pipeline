from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.schemas.classification import IssueType


STATE_CODES = [
    "AL",
    "AK",
    "AZ",
    "AR",
    "CA",
    "CO",
    "CT",
    "DE",
    "FL",
    "GA",
    "HI",
    "ID",
    "IL",
    "IN",
    "IA",
    "KS",
    "KY",
    "LA",
    "ME",
    "MD",
    "MA",
    "MI",
    "MN",
    "MS",
    "MO",
    "MT",
    "NE",
    "NV",
    "NH",
    "NJ",
    "NM",
    "NY",
    "NC",
    "ND",
    "OH",
    "OK",
    "OR",
    "PA",
    "RI",
    "SC",
    "SD",
    "TN",
    "TX",
    "UT",
    "VT",
    "VA",
    "WA",
    "WV",
    "WI",
    "WY",
]


PROFILE_RULES: dict[str, dict[str, Any]] = {
    "fraud_fast": {
        "sla_window": "10 calendar days",
        "required_actions": [
            "Secure account access and preserve evidence",
            "Investigate disputed transactions and timeline",
            "Provide interim status updates until resolution",
        ],
        "regulatory_basis": "Dummy regular norm aligned to Regulation E fraud/error handling",
    },
    "billing_standard": {
        "sla_window": "21 calendar days",
        "required_actions": [
            "Validate fee/interest or billing calculation",
            "Pause incremental disputed penalties where applicable",
            "Provide written findings and correction path",
        ],
        "regulatory_basis": "Dummy regular norm aligned to Regulation Z billing error framework",
    },
    "credit_reporting": {
        "sla_window": "30 calendar days",
        "required_actions": [
            "Validate furnishing data and dispute context",
            "Coordinate reinvestigation where applicable",
            "Send written correction or no-change rationale",
        ],
        "regulatory_basis": "Dummy regular norm aligned to FCRA dispute/reinvestigation baseline",
    },
    "debt_collection": {
        "sla_window": "21 calendar days",
        "required_actions": [
            "Verify debt ownership/amount and notice compliance",
            "Pause disputed collection actions while review is active",
            "Provide written verification and next-step rights",
        ],
        "regulatory_basis": "Dummy regular norm aligned to FDCPA validation/communication baseline",
    },
    "lending": {
        "sla_window": "30 calendar days",
        "required_actions": [
            "Review account history and payment events",
            "Confirm contractual terms and servicing obligations",
            "Provide written determination and remediation steps",
        ],
        "regulatory_basis": "Dummy regular norm: lending-servicing baseline",
    },
    "service_general": {
        "sla_window": "30 calendar days",
        "required_actions": [
            "Acknowledge complaint receipt",
            "Open investigation and assign owner",
            "Provide written update and final outcome",
        ],
        "regulatory_basis": "Dummy regular norm: general complaint baseline",
    },
}


def main() -> int:
    issue_norms: dict[str, dict[str, Any]] = {}
    for issue in IssueType:
        key = normalize_issue(issue.value)
        profile = classify_issue(issue.value)
        rule = dict(PROFILE_RULES[profile])
        rule["profile"] = profile
        rule["issue_display"] = issue.value
        issue_norms[key] = rule

    state_defaults = {
        state: {
            "sla_window": "30 calendar days",
            "required_actions": [
                "Acknowledge complaint receipt",
                "Open investigation and assign owner",
                "Provide written update and final outcome",
            ],
            "regulatory_basis": f"Dummy {state} state default norm",
        }
        for state in STATE_CODES
    }

    state_overrides: dict[str, dict[str, Any]] = {
        "CA": {
            "issues": {
                key: {
                    "sla_window": "15 calendar days",
                    "regulatory_basis": "Dummy CA billing-accelerated norm",
                }
                for key, rule in issue_norms.items()
                if rule.get("profile") == "billing_standard"
            }
        },
        "NY": {
            "issues": {
                key: {
                    "sla_window": "7 calendar days",
                    "regulatory_basis": "Dummy NY fraud-accelerated norm",
                }
                for key, rule in issue_norms.items()
                if rule.get("profile") == "fraud_fast"
            }
        },
        "TX": {
            "issues": {
                key: {
                    "sla_window": "21 calendar days",
                    "regulatory_basis": "Dummy TX billing norm",
                }
                for key, rule in issue_norms.items()
                if rule.get("profile") == "billing_standard"
            }
        },
    }

    payload = {
        "version": "0.2-regular-norms",
        "description": (
            "Generated dummy policy rules: all 50 states and all CFPB issue keys. "
            "Values are regular norms for simulation, not legal advice."
        ),
        "issue_key_count": len(issue_norms),
        "state_count": len(STATE_CODES),
        "state_codes": STATE_CODES,
        "issue_norms": issue_norms,
        "state_defaults": state_defaults,
        "state_overrides": state_overrides,
    }

    root = Path(__file__).resolve().parent
    out_path = root / "dummy_policy_rules.json"
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"wrote {out_path}")
    print(f"issue keys: {len(issue_norms)}; states: {len(STATE_CODES)}")
    return 0


def classify_issue(issue_value: str) -> str:
    text = issue_value.lower()
    if contains_any(
        text,
        [
            "fraud",
            "unauthorized transaction",
            "lost or stolen money order",
            "identity theft",
            "security freeze",
            "credit monitoring",
        ],
    ):
        return "fraud_fast"
    if contains_any(
        text,
        [
            "fee",
            "interest",
            "billing",
            "wrong amount",
            "exchange rate",
            "overdraft",
        ],
    ):
        return "billing_standard"
    if contains_any(
        text,
        [
            "credit report",
            "report",
            "credit score",
            "incorrect information",
            "investigation into an existing issue",
            "improper use of your report",
        ],
    ):
        return "credit_reporting"
    if contains_any(
        text,
        [
            "collect debt",
            "communication tactics",
            "threatened",
            "legal action",
            "written notification about debt",
            "false statements",
        ],
    ):
        return "debt_collection"
    if contains_any(
        text,
        [
            "mortgage",
            "loan",
            "lease",
            "repossession",
            "struggling to pay",
            "payment process",
        ],
    ):
        return "lending"
    return "service_general"


def contains_any(text: str, candidates: list[str]) -> bool:
    return any(item in text for item in candidates)


def normalize_issue(issue_type: str) -> str:
    token = issue_type.strip().upper().replace("-", "_").replace(" ", "_")
    keep: list[str] = []
    for ch in token:
        if ch.isalnum() or ch == "_":
            keep.append(ch)
    return "".join(keep)


if __name__ == "__main__":
    raise SystemExit(main())
