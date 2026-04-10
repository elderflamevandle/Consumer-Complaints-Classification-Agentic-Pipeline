import json
from src.graph.pipeline import build_graph, run_complaint

def main():
    print("Building the FinComplaint LangGraph pipeline...")
    graph = build_graph()
    
    sample_complaint = (
        "Someone stole my identity last week, opened a checking account "
        "using my name, and started transferring money out of my real account! "
        "My name is Jane Smith, SSN 111-22-3333."
    )
    
    print("\n--- SAMPLE INPUT ---")
    print(sample_complaint)
    print("\nRunning the pipeline... This may take a minute depending on LLM responses.")
    
    # Run the graph (using "NY" to fetch New York regulations from the local MCP server)
    final_state = run_complaint(graph, complaint_text=sample_complaint, state_code="NY")
    
    print("\n\n" + "="*50)
    print(" PIPELINE EXECUTION COMPLETE ")
    print("="*50)
    
    # Print the Scrubbed Text
    print("\n[1] SCRUBBED TEXT (After PII Intake):")
    intake = final_state.get('intake')
    if intake:
        print(f" -> {intake.scrubbed_text}")

    # Print Classification Results
    print("\n[2] CLASSIFICATION:")
    classification = final_state.get('classification')
    if classification:
        print(f" -> Product: {classification.product_type.value}")
        print(f" -> Issue: {classification.issue_type.value}")
        print(f" -> Severity: {classification.severity.value}")
    
    # Print MCP Server Policy
    print("\n[3] POLICY REQUIRED (From MCP Server):")
    remediation = final_state.get('remediation')
    if remediation and hasattr(remediation, 'model_dump_json'):
        print(remediation.model_dump_json(indent=2))
    
    # Print Audit Loop attempts
    print(f"\n[4] WRITER / AUDITOR LOOPS REQUIRED: {final_state.get('rewrite_count', 0)}")

    # Print the Final AI Generated Response sent to customer
    print("\n[5] FINAL EMAILED RESPONSE:")
    print("-" * 40)
    print(final_state.get("response_draft"))
    print("FINAL STATE -->", final_state)
    print("-" * 40)

if __name__ == "__main__":
    main()
