# FinComplaint AI Agentic Pipeline 🏦🤖

A highly-structured, deterministic, multi-agent pipeline designed to securely and compliantly triage financial consumer complaints. 

Unlike generic unconstrained agent workflows, FinComplaint AI enforces strict schemas, uses Retrieval-Augmented Generation (RAG) against real historical Consumer Financial Protection Bureau (CFPB) data, and incorporates a Model Context Protocol (MCP) server to ensure all AI responses adhere strictly to localized regulatory SLA laws.

---

## 🛠 Flow Architecture & Components

The pipeline processes complaints through a deterministic sequence. Each agent/node uses robust Pydantic schemas for data passing and includes automated "repair" loops if the LLM hallucinates non-compliant data.

### 1. Intake Processing (PII Scrubber)
* **Location:** `src/intake/pipeline.py`
* **Role:** The pre-LLM firewall.
* **Function:** Identifies and redacts sensitive Personally Identifiable Information (PII) such as Social Security Numbers, phone numbers, and names using local logic and heuristics before any data reaches an LLM.

### 2. Classifier Agent
* **Location:** `src/agents/classifier.py`
* **Role:** Taxonomy mapper.
* **Function:** Analyzes the scrubbed text and deterministically extracts five keys: `product_type`, `issue_type`, `severity`, `compliance_risk`, and an internal `confidence` score.

### 3. Routing Gateway (HITL Circuit Breaker)
* **Location:** `src/graph/routing.py`
* **Role:** The safety valve.
* **Function:** Not an LLM. It's a deterministic logic gate evaluating the Classifier's output. If the risk is high (e.g., Critical Severity or low confidence), the pipeline pauses and requires a Human-in-the-Loop review before continuing automation.

### 4. Root Cause Agent (RAG)
* **Location:** `src/agents/root_cause.py`
* **Role:** Historical diagnostician.
* **Function:** Queries a local Chroma Vector Database populated with real historical CFPB complaints. It compares the current complaint to the top 5 historical precedents to diagnose the root cause with evidence-based citations.

### 5. Remediator Agent (MCP Grounding)
* **Location:** `src/agents/remediator.py` & `src/tools/mcp_policy_client.py`
* **Role:** The compliance action-planner.
* **Function:** Queries a **Local MCP Server** (`mcp_server/server.py`) for state-specific SLA laws and required actions regarding the specific issue. It feeds these strict legal requirements into the LLM to formulate an actionable, legally grounded resolution plan.

### 6. Response Generation Loop (Actor-Critic)
* **Location:** `src/graph/response_loop.py` (comprising `writer.py` and `auditor.py`)
* **Role:** The customer-facing draft creators.
* **Function:** 
  * The **Writer** drafts a strict 4-block email response (Acknowledgment, Findings, Action Steps, Timeline).
  * The **Auditor** acts as the legal reviewer, failing drafts that overcommit, admit liability, or miss MCP policy citations.
  * If failed, the draft loops back to the Writer for a rewrite.

### 7. Explainer Agent (Transparency Layer)
* **Location:** `src/agents/explainer.py`
* **Role:** The audit trail generator.
* **Function:** Processes all actions taken by previous agents to generate a clear, deterministic 5-7 bullet point summary for an internal SQLite database (`data/audit.db`), proving *why* the AI made the decisions it did.

---

## 🔍 The MCP Level Explained (Model Context Protocol)

To ensure the AI doesn't hallucinate regulations or promise illegal SLA timelines, FinComplaint uses the Model Context Protocol to fetch external ground-truth state laws before writing action plans.

1. The `RemediatorAgent` halts and calls the `MCPPolicyClient`.
2. The client spins up an isolated subprocess querying `mcp_server/server.py` with the extracted `Issue Type` and `State Code` (e.g., FRAUD in NY).
3. The server acts as a database lookup (mocked in `mock_regulations.json`), returning strict laws such as "7 calendar day SLA" and "Required: provisional credit".
4. The Remediator is forced to ingest this strict JSON payload into its prompt, grounding the subsequent action plan in reality.

---

## 🏃 Example Walkthrough

**The Input:**
> *"Someone stole my identity last week, opened a checking account using my name, and started transferring money out of my real account! My name is Jane Smith, SSN 111-22-3333."*

**The Pipeline Flow:**
1. **Intake:** Scrubs "Jane Smith" and "111-22-3333".
2. **Classifier:** Assesses as `BANK_ACCOUNT`, `FRAUD`, `CRITICAL` Severity.
3. **Router:** Flags for human review due to critical severity. (Approved to continue).
4. **Root Cause:** Locates historical CFPB fraud cases; diagnoses "Account Takeover".
5. **Remediator:** Hits MCP Server. Returns NY SLA law requiring a 7-day turnaround.
6. **Writer/Auditor:** Writes response. Auditor rejects draft 1 for saying "We guarantee a fix". Writer creates Draft 2 without the guarantee. Auditor passes Draft 2.
7. **Explainer:** Saves the bulleted decision chain to the audit log.

**Final Generated Output:**
> **Acknowledgment:** We understand the distressing nature of unauthorized transfers and appreciate you reporting this suspected identity theft immediately.
> **Findings:** Our initial review confirms the need for an urgent investigation into the unauthorized checking account activity. 
> **Action Steps:** We have escalated your case to our specialized fraud unit. Temporary protections and provisional credits will be applied while the investigation continues.
> **Timeline / Next Steps:** We will communicate case statuses with you every 48 hours aiming for a resolution within the required 7 calendar day window.

---

## 🚀 Usage

For setup instructions, testing, data compilation, and basic script execution, refer to the root `README.md`.
