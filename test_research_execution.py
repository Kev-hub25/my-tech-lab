
from app.research_execution_engine import execute_research_task

test_task = {
    "task_key": "TEST-CRDB-001",
    "opportunity_key": "CRDB_TEST",
    "opportunity_title": "CRDB Bank Research Test",
    "subject": "CRDB Bank",
    "domain": "FINANCIAL_MARKET",
    "geography": "Tanzania",
    "research_mode": "DEEP",
    "task": (
        "Find reliable information about CRDB Bank's "
        "financial performance, valuation, share price, and risks."
    ),
    "purpose": (
        "Test whether MY TECH LAB can retrieve evidence "
        "for evaluating a potential investment opportunity."
    ),
}

result = execute_research_task(test_task)

print("\n=== MY TECH LAB RESEARCH TEST ===")
print("Status:", result.get("status"))
print("Query:", result.get("query"))
print("Provider:", result.get("provider"))
print("Findings:", len(result.get("findings", [])))

for i, finding in enumerate(result.get("findings", []), start=1):
    print(f"\n--- Finding {i} ---")
    print("Title:", finding.get("title"))
    print("Domain:", finding.get("domain"))
    print("Published:", finding.get("published_date"))
    print("URL:", finding.get("url"))
    print("Summary:", finding.get("summary"))

if result.get("error"):
    print("\nError:", result["error"])

if result.get("caveats"):
    print("\nCaveats:", result["caveats"])
