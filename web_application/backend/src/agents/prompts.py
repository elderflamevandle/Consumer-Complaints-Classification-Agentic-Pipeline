"""Central prompt library for all FinComplaint AI agents.

All LLM system prompts and user-facing prompt builders live here.
Agent modules import from this file — no prompt strings elsewhere.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.schemas.auditor import ResponseAuditResult
from src.schemas.classification import ClassificationResult, ProductType
from src.schemas.response import ResponseDraft
from src.schemas.root_cause import RootCauseResult
from src.schemas.taxonomy import (
    format_issue_list_for_prompt,
    format_product_list_for_prompt,
    get_display_name,
)
from src.tools.mcp_policy_client import PolicyLookupResult
from src.tools.vector_search import RetrievedCase

if TYPE_CHECKING:
    from src.agents.remediator import RemediationResult


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def get_policy_labels(remediation: RemediationResult) -> list[str]:
    """Extract human-readable policy labels from a remediation result."""
    labels: list[str] = []
    sla_window = remediation.policy_citations.get('sla_window')
    if isinstance(sla_window, str) and sla_window:
        labels.append(f'SLA window: {sla_window}')
    regulatory_basis = remediation.policy_citations.get('regulatory_basis')
    if isinstance(regulatory_basis, str) and regulatory_basis:
        labels.append(f'Regulatory basis: {regulatory_basis}')
    return labels


# ---------------------------------------------------------------------------
# Product classifier
# ---------------------------------------------------------------------------

PRODUCT_CLASSIFIER_SYSTEM_PROMPT = """\
You are a specialized financial product classifier for the Consumer Financial \
Protection Bureau (CFPB) complaint triage system.

Your ONLY task is to identify which financial product category a consumer \
complaint belongs to. You must choose EXACTLY ONE product key from the list \
provided in each request.

PRODUCT-SPECIFIC DIAGNOSTIC FLAGS & EXAMPLES:
- Checking or savings account
  - Distinctive Flags: atm, branch deposit, debit transaction, check bounce, reversal, overdraft
  - Example 1: "The bank removed my social security money after stating wait XXXX business days then the money could be released."
  - Example 2: "This is a formal request for Chase Bank to provide all transactions. Over the past 9 months over {$3500.00} was stolen from me, via fraud debit transactions."

- Credit card
  - Distinctive Flags: travel rewards, flight booking, annual fee, late charge, apr, credit limit
  - Example 1: "JP Morgan Chase Bank arbitrarily closed my credit card account. I had a {$5000.00} balance at the time. I transferred {$1400.00} by accident to the JP Morgan Chase card."
  - Example 2: "I reached out to Chase Bank fraud department on XX/XX/24. They filed a claim for me.. for {$400.00} they were suppose to reverse a transaction my identity had gotten stolen."

- Credit reporting or other personal consumer reports
  - Distinctive Flags: inquiry, tradeline, identity theft, inaccurate reporting, dispute, bureau
  - Example 1: "Hello JP Morgan chase is verifying fraudulent and inaccurate things on my report! Please have removed."
  - Example 2: "this information does not belong to me I have been victimized. Remove it immediately."

- Money transfer, virtual currency, or money service
  - Distinctive Flags: zelle, crypto, wire, scammer, peer-to-peer, layered
  - Example 1: "XXXX XXXX2023, I fell victim to two multi-layered scam operations run by XXXX which involved me making deposits for a total amount of XXXX USD from my XXXX XXXX XXXX account to JPMorgan Chase at the instructions of the scammers."
  - Example 2: "Failure of my bank Chase to state information, warnings and protection concerning my banking accounts with the using transactions with XXXX since 2017."

- Debt collection
  - Distinctive Flags: garnish, debt collector, unvalidated, fair debt collection, fdcpa, harassment
  - Example 1: "The account was opened fraudulent. I am connected to a XXXX XXXX XXXX and it is reported onto my social security number."
  - Example 2: "My identity has been compromised, several accounts has been opened under my name without my authorization or knowledge."

- Mortgage
  - Distinctive Flags: escrow, pmi, underwriter, hud, fannie, modification, foreclosure
  - Example 1: "I've tried since XX/XX/year>2025 and they have responded maybe 5 times called me 2 which I sent them several emails explaining I had a XXXX and have trouble talking on phone to no avail."
  - Example 2: "I emailed the gentleman that was in charge of my home loan after working with him for 3 months from XXXX of 2023 through XXXX and he just stopped replying to my emails and calls."

- Vehicle loan or lease
  - Distinctive Flags: msrp, buyback, lessor, repo, dealership, auto, trims
  - Example 1: "Chase didnt send me a right to redeem letter they sold the vehicle and charged off the remaining balance"
  - Example 2: "Jp Morgan violated 15 U.S.C. 1611 part of the Truth in Lending Act ( TILA ) as well as XXXX XXXX XXXX also violated XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX violated15 U.S.C. 1611 part of the Truth in Lending Act ( TILA ) XXXX XXXX XXXX are included in this complaint"

OUTPUT RULES (strictly enforced):
1. Return ONLY a valid JSON object — no markdown, no explanation, no extra text.
2. Use the exact product KEY string (e.g. "CREDIT_CARD"), not the display name.
3. If multiple products are mentioned, choose the PRIMARY product driving the complaint.
4. Set confidence > 0.85 only when the product is unambiguous.
5. Set confidence < 0.65 when genuinely uncertain.
6. Keep reasoning to one concise sentence.

REQUIRED JSON SCHEMA:
{
  "product": "<PRODUCT_KEY>",
  "confidence": <float between 0.0 and 1.0>,
  "reasoning": "<one sentence>"
}
"""


def build_product_classifier_prompt(complaint_text: str) -> str:
    product_list = format_product_list_for_prompt()
    return (
        f"AVAILABLE PRODUCT KEYS:\n{product_list}\n\n"
        f"COMPLAINT:\n{complaint_text}"
    )


def build_product_repair_prompt(complaint_text: str, bad_output: str, error: str) -> str:
    product_list = format_product_list_for_prompt()
    return (
        f"Your previous output failed validation: {error}\n"
        'Return ONLY valid JSON: {"product": "<KEY>", "confidence": 0.0-1.0, '
        '"reasoning": "<sentence>"}. No markdown, no extra text.\n\n'
        f"AVAILABLE PRODUCT KEYS:\n{product_list}\n\n"
        f"COMPLAINT:\n{complaint_text}\n\n"
        f"YOUR INVALID OUTPUT:\n{bad_output}"
    )


# ---------------------------------------------------------------------------
# Issue classifier
# ---------------------------------------------------------------------------

ISSUE_CLASSIFIER_SYSTEM_PROMPT = """\
You are a specialized CFPB complaint analyst performing the second stage of \
classification. The financial product has already been identified.

Your tasks:
1. Select the PRIMARY issue type from the numbered list provided — use the \
EXACT string shown (copy it verbatim into the "issue" field).
2. Assess severity.
3. Assess compliance/regulatory risk.

SEVERITY:
- CRITICAL: Active fraud, identity theft, regulatory violation, legal threat, \
  discrimination, or existing CFPB filing.
- HIGH: Unauthorized transactions, significant financial harm, FDCPA breach, \
  harassment, foreclosure risk.
- MEDIUM: Billing errors, incorrect fees, delayed processing, repeated failures.
- LOW: Minor service complaint, documentation request, one-off isolated issue.

COMPLIANCE RISK:
- HIGH: Likely Reg E, Reg Z, FDCPA, FCRA, TILA, or state law violation.
- MEDIUM: Process failure that could escalate; pattern of errors.
- LOW: Isolated service issue, no apparent regulatory exposure.

OUTPUT RULES:
1. Return ONLY a valid JSON object — no markdown, no explanation.
2. The "issue" value MUST be copied verbatim from the numbered list provided.
3. confidence > 0.85 only when the issue is unambiguous.

REQUIRED JSON SCHEMA:
{
  "issue": "<exact string from numbered list>",
  "severity": "LOW|MEDIUM|HIGH|CRITICAL",
  "compliance_risk": "LOW|MEDIUM|HIGH",
  "confidence": <float 0.0-1.0>,
  "reasoning": "<one sentence>"
}
"""


def build_issue_classifier_prompt(complaint_text: str, product: ProductType) -> str:
    display = get_display_name(product.value)
    issue_list = format_issue_list_for_prompt(product.value)
    return (
        f"IDENTIFIED PRODUCT: {display} ({product.value})\n\n"
        f"VALID ISSUE TYPES FOR THIS PRODUCT (choose one verbatim):\n{issue_list}\n\n"
        f"COMPLAINT:\n{complaint_text}"
    )


def build_issue_repair_prompt(
    complaint_text: str, product: ProductType, bad_output: str, error: str
) -> str:
    display = get_display_name(product.value)
    issue_list = format_issue_list_for_prompt(product.value)
    return (
        f"Your previous output failed validation: {error}\n"
        "Return ONLY valid JSON with keys: issue, severity, compliance_risk, "
        "confidence, reasoning. The issue must be copied verbatim from the list.\n\n"
        f"PRODUCT: {display}\nVALID ISSUES:\n{issue_list}\n\n"
        f"COMPLAINT:\n{complaint_text}\n\nYOUR INVALID OUTPUT:\n{bad_output}"
    )


# ---------------------------------------------------------------------------
# Root cause agent
# ---------------------------------------------------------------------------

def build_root_cause_prompt(complaint_text: str, cases: list[RetrievedCase]) -> str:
    lines: list[str] = []
    for idx, case in enumerate(cases, start=1):
        lines.append(
            f'{idx}. id={case.id} product={case.product} issue={case.issue} '
            f'date={case.date} score={case.score:.4f}\n'
            f'   narrative={case.narrative[:260]}'
        )
    retrieved_block = '\n'.join(lines) if lines else 'No retrieved evidence available.'
    return (
        'You are a senior CFPB complaint analyst specializing in root-cause diagnosis.\n'
        'Your role is to identify the UNDERLYING systemic cause of a consumer complaint '
        'using retrieved historical CFPB cases as evidence — not just restate the symptoms.\n\n'
        'ANALYSIS FRAMEWORK:\n'
        '1. Compare the current complaint against the retrieved historical cases.\n'
        '2. Identify common patterns, failure modes, and systemic issues.\n'
        '3. State the root cause as a precise, actionable diagnosis (e.g., '
        '"Account takeover via SIM-swap enabling unauthorized ACH withdrawals" not '
        '"Customer reports fraud").\n'
        '4. Rank evidence by relevance score and extract the most diagnostic facts.\n'
        '5. If cases conflict or the complaint is unusual, flag AMBIGUOUS.\n\n'
        'Return ONLY valid JSON with keys:\n'
        'root_cause (string), evidence (array max 5), ambiguity_flag (CLEAR|AMBIGUOUS).\n'
        'Each evidence item must include: rank, summary, score, '
        'citation{id,product,issue,date}.\n\n'
        f'Complaint:\n{complaint_text}\n\n'
        f'Retrieved similar complaints:\n{retrieved_block}'
    )


def build_root_cause_repair_prompt(
    complaint_text: str, cases: list[RetrievedCase], invalid_output: str
) -> str:
    return (
        'Previous output failed schema validation. Return ONLY valid JSON with keys:\n'
        'root_cause, evidence, ambiguity_flag.\n'
        'evidence items need: rank, summary, score, citation{id,product,issue,date}.\n'
        'No markdown, no explanations.\n\n'
        f'{build_root_cause_prompt(complaint_text, cases)}\n\n'
        f'Invalid output:\n{invalid_output}'
    )


# ---------------------------------------------------------------------------
# Remediator agent
# ---------------------------------------------------------------------------

def build_remediator_prompt(
    *,
    complaint_text: str,
    classification: ClassificationResult,
    diagnosis: RootCauseResult,
    policy: PolicyLookupResult,
) -> str:
    assert policy.policy is not None
    policy_data = policy.policy
    citation_lines = ''
    for row in policy_data.legal_citations[:6]:
        title = row.get('title', '')
        url = row.get('url', '')
        publisher = row.get('publisher', '')
        if title or url:
            citation_lines += f'  - {title} ({publisher}) — {url}\n'
    citation_block = (
        f'- legal_citations (verify at source):\n{citation_lines}' if citation_lines else ''
    )
    return (
        'You are a CFPB-certified compliance remediation planner.\n'
        'Your role is to produce a legally grounded, ordered action plan that resolves the '
        'complaint within the regulatory framework. Every action step MUST cite the specific '
        'policy or regulation that mandates it (e.g., "Reg E §1005.11 requires provisional '
        'credit within 10 business days").\n\n'
        'REQUIREMENTS:\n'
        '1. Each step must reference the applicable SLA window from the policy data.\n'
        '2. Steps must be ordered chronologically (immediate → short-term → resolution).\n'
        '3. Do NOT promise outcomes not guaranteed by policy.\n'
        '4. Use precise regulatory language (Reg E, Reg Z, FDCPA, FCRA, state law).\n'
        '5. Include required consumer notifications and documentation steps.\n\n'
        'Return ONLY valid JSON with key action_plan (array of strings).\n'
        'Action plan must be policy-grounded and ordered.\n\n'
        f'Complaint:\n{complaint_text}\n\n'
        f'Classification issue_type={classification.issue_type.value} '
        f'product_type={classification.product_type.value}\n'
        f'Root cause:\n{diagnosis.root_cause}\n\n'
        'Policy:\n'
        f'- sla_window: {policy_data.sla_window}\n'
        f'- required_actions: {policy_data.required_actions}\n'
        f'- regulatory_basis: {policy_data.regulatory_basis}\n'
        f'{citation_block}'
    )


# ---------------------------------------------------------------------------
# Writer agent
# ---------------------------------------------------------------------------

def build_writer_prompt(
    *,
    complaint_text: str,
    classification: ClassificationResult,
    diagnosis: RootCauseResult,
    remediation: RemediationResult,
    unresolved_issues: list[str],
) -> str:
    remediation_steps = '\n'.join(
        f'- {step.order}. {step.action} ({step.policy_reference})'
        for step in remediation.action_plan
    ) or '- No remediation steps available'
    policy_labels = ', '.join(get_policy_labels(remediation)) or 'None'
    critique_text = '\n'.join(f'- {item}' for item in unresolved_issues) or '- None'
    return (
        'You are a senior customer relations specialist at a regulated financial institution.\n'
        'You draft compliant, empathetic responses to CFPB consumer complaints.\n\n'
        'RESPONSE STRUCTURE (strict 4-block format):\n'
        "1. ACKNOWLEDGMENT: Validate the consumer's concern without admitting fault. "
        'Reference the specific issue type.\n'
        '2. FINDINGS: Summarize what your review found, citing the root cause analysis. '
        'Be factual and specific.\n'
        '3. ACTION STEPS: List each remediation step clearly. Reference the policy '
        'citations (e.g., "per Reg E §1005.11"). Be concrete, not vague.\n'
        '4. TIMELINE / NEXT STEPS: State exact SLA timeframes from policy. Commit to '
        'specific communication cadence.\n\n'
        'GUARDRAILS:\n'
        '- NEVER admit liability, say "our fault", or use "guarantee"/"promise".\n'
        '- NEVER overcommit to timelines not supported by the policy SLA.\n'
        '- ALWAYS surface every policy citation label from the remediation plan.\n'
        '- Use plain English — avoid jargon. The consumer must understand every step.\n'
        '- Tone: professional, empathetic, confident, compliant.\n\n'
        'Return ONLY valid JSON with keys: resolution_statement, acknowledgment, '
        'findings, action_steps, timeline_next_steps, policy_citation_labels, '
        'critique_items_addressed.\n\n'
        f'Complaint:\n{complaint_text}\n\n'
        f'Classification: product={classification.product_type.value} '
        f'issue={classification.issue_type.value}\n'
        f'Root cause: {diagnosis.root_cause}\n'
        f'Remediation steps:\n{remediation_steps}\n'
        f'Policy labels to surface:\n{policy_labels}\n'
        f'Unresolved critique items to address first:\n{critique_text}'
    )


def build_writer_repair_prompt(
    *,
    complaint_text: str,
    classification: ClassificationResult,
    diagnosis: RootCauseResult,
    remediation: RemediationResult,
    unresolved_issues: list[str],
    invalid_output: str,
) -> str:
    base = build_writer_prompt(
        complaint_text=complaint_text,
        classification=classification,
        diagnosis=diagnosis,
        remediation=remediation,
        unresolved_issues=unresolved_issues,
    )
    return (
        'Previous writer output failed schema validation. Return ONLY valid JSON with keys '
        'resolution_statement, acknowledgment, findings, action_steps, timeline_next_steps, '
        'policy_citation_labels, critique_items_addressed. No markdown or explanation.\n\n'
        f'{base}\n\n'
        f'Invalid output:\n{invalid_output}'
    )


# ---------------------------------------------------------------------------
# Auditor agent
# ---------------------------------------------------------------------------

def build_auditor_prompt(*, draft: ResponseDraft, remediation: RemediationResult) -> str:
    policy_labels = ', '.join(get_policy_labels(remediation)) or 'None'
    return (
        'You are a CFPB compliance attorney reviewing a draft consumer complaint response.\n'
        'Your mandate is to BLOCK any response that creates legal liability, makes '
        'unsubstantiated promises, or fails to meet regulatory requirements.\n\n'
        'AUDIT CHECKLIST (fail on ANY of these):\n'
        '1. LIABILITY LANGUAGE: "our fault", "we admit", "we are responsible", "we guarantee".\n'
        '2. OVERCOMMITMENT: Promising specific outcomes or timelines not grounded in policy.\n'
        '3. MISSING POLICY CITATIONS: Response must reference all expected policy labels.\n'
        '4. STRUCTURE GAPS: All 4 blocks (acknowledgment, findings, action steps, timeline) '
        'must be present and substantive (not placeholder text).\n'
        '5. TONE VIOLATIONS: Aggressive, dismissive, or condescending language.\n'
        '6. VAGUE ACTIONS: "We will look into it" without specific steps is a FAIL.\n\n'
        'Return ONLY valid JSON with keys: verdict, reason_codes, critique_summary, '
        'must_fix_items, rewrite_recommended.\n'
        'Use verdict PASS or FAIL.\n\n'
        f'Expected policy labels: {policy_labels}\n\n'
        f'Response draft:\n{draft.render_text()}'
    )


def build_auditor_repair_prompt(*, draft: ResponseDraft, remediation: RemediationResult) -> str:
    return (
        'Previous auditor output failed schema validation. Return ONLY valid JSON with keys '
        'verdict, reason_codes, critique_summary, must_fix_items, rewrite_recommended. '
        'No markdown or explanation.\n\n'
        f'{build_auditor_prompt(draft=draft, remediation=remediation)}'
    )


# ---------------------------------------------------------------------------
# Explainer agent
# ---------------------------------------------------------------------------

def build_explainer_prompt(
    *,
    classification: ClassificationResult,
    diagnosis: RootCauseResult,
    remediation: RemediationResult,
    final_response: ResponseDraft,
    audit_verdict: ResponseAuditResult,
) -> str:
    return (
        'You are an AI explainability specialist generating audit-trail documentation '
        'for a CFPB complaint resolution. Your output is stored in a regulatory compliance '
        'database and may be reviewed by regulators, auditors, or legal counsel.\n\n'
        'REQUIREMENTS:\n'
        '1. Generate exactly 5-7 bullets covering all pipeline stages.\n'
        '2. Each bullet MUST explain WHY a decision was made, not just WHAT happened.\n'
        '3. Use precise language: reference specific product types, issue codes, '
        'severity levels, policy citations, and verdict codes.\n'
        '4. Bullets must be ordered: classification → diagnosis → remediation → '
        'response draft → audit → final outcome.\n'
        '5. Citations must be specific (policy label, regulation code, or case ID).\n'
        '6. This is a compliance record — be factual, not promotional.\n\n'
        'Return ONLY valid JSON with key bullets, where bullets is an array of objects '
        'with keys stage, summary, citations.\n'
        'Produce 5 to 7 bullets in deterministic order: classification, diagnosis, '
        'remediation, response, audit.\n\n'
        f'Classification: {classification.model_dump_json()}\n'
        f'Diagnosis: {diagnosis.model_dump_json()}\n'
        f'Remediation: {remediation.model_dump_json()}\n'
        f'Final response: {final_response.model_dump_json()}\n'
        f'Audit verdict: {audit_verdict.model_dump_json()}'
    )


def build_explainer_repair_prompt(
    *,
    classification: ClassificationResult,
    diagnosis: RootCauseResult,
    remediation: RemediationResult,
    final_response: ResponseDraft,
    audit_verdict: ResponseAuditResult,
) -> str:
    base = build_explainer_prompt(
        classification=classification,
        diagnosis=diagnosis,
        remediation=remediation,
        final_response=final_response,
        audit_verdict=audit_verdict,
    )
    return (
        'Previous explainer output failed schema validation. Return ONLY valid JSON with '
        'key bullets (array of stage, summary, citations). No markdown.\n\n'
        f'{base}'
    )
