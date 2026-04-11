import os
import json
from src.graph.pipeline import build_graph, run_complaint

def main():
    print("🚀 [1/4] Booting up FinComplaint AI Agents and Building LangGraph...")
    # This automatically instantiates all your LLM Agents and MCP Clients
    graph = build_graph()
    
    # Let's test it with a sample consumer complaint
    sample_complaint = (
        "Someone stole my identity last week, opened a checking account "
        "using my name, and started transferring money out of my real account! "
        "My name is Jane Smith, SSN 111-22-3333."
    )
    
    # State code indicates what compliance rules the MCP Server will fish for
    state_for_mcp = "NY"

    print("\n📩 [2/4] NEW COMPLAINT INGRESS:")
    print("-" * 50)
    print(sample_complaint)
    print("-" * 50)
    
    print(f"\n⚙️ [3/4] Running Agents through the Pipeline (Fetching rules for {state_for_mcp})...")
    # This single function pushes the text through all interacting agents!
    final_state = run_complaint(
        graph, 
        complaint_text=sample_complaint, 
        state_code=state_for_mcp
    )
    
    print("\n✅ [4/4] PIPELINE EXECUTION COMPLETE. Extracting Agent Findings...")
    print("=" * 60)
    
    # 1. Intake Agent (PII Scrubbing)
    print("\n🕵️ INTAKE AGENT (PII Scrubbed):")
    intake = final_state.get('intake')
    if intake:
        print(f" -> {intake.scrubbed_text}")

    # 2. Classifier Agents
    print("\n🧠 CLASSIFIER AGENTS:")
    classification = final_state.get('classification')
    if classification:
        print(f" -> Found Product Type : {classification.product_type.value}")
        print(f" -> Found Issue Type   : {classification.issue_type.value}")
        print(f" -> Assessed Severity  : {classification.severity.value}")
    
    # 3. Root Cause Agent (RAG)
    print("\n📚 ROOT CAUSE AGENT:")
    diagnosis = final_state.get('diagnosis')
    if diagnosis:
        print(f" -> Summary: {diagnosis.root_cause}")
    
    # 4. Remediator Agent & MCP Server (Compliance Rules)
    print("\n⚖️ MCP SERVER & REMEDIATOR AGENT:")
    remediation = final_state.get('remediation')
    if remediation:
        # We can see the compliance data the MCP gave to the Remediator
        citations = remediation.policy_citations
        print(f" -> Required SLA Deadline: {citations.get('sla_window', 'None')}")
        print(f" -> Source               : {citations.get('regulatory_basis', 'None')[:150]}...")
        print("\n -> Steps Agent Proposed :")
        for step in remediation.action_plan:
            print(f"    {step.order}. {step.action}")
            
    # 5. Review & Audit details
    print(f"\n🔄 AUDITOR AGENT REWRITE LOOPS: {final_state.get('rewrite_count', 0)}")

    # 6. Final Writer Agent Output
    print("\n✉️ FINAL APPROVED CUSTOMER RESPONSE (Writer Agent):")
    print("*" * 60)
    print(final_state.get("response_draft"))
    print("*" * 60)

if __name__ == "__main__":
    main()