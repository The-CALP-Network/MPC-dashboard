"""
Test script to check what fields are available in the HPC Plan API for plan 1276 (Syria 2025)
"""
import sys
import json

try:
    import requests
except ImportError:
    print("requests module not available - showing expected API structure based on documentation")
    print("\nExpected structure for plan API response:")
    print("""
    {
      "data": {
        "id": 1276,
        "planVersion": {
          "id": ...,
          "name": "Syrian Arab Republic",
          "code": "...",
          "startDate": "2025-01-01",
          "endDate": "2025-12-31"
        },
        "requirements": ...,
        "totalFunding": ...,
        "funding": ...
      }
    }
    """)
    sys.exit(0)

# Try to fetch plan 1276
url = "https://api.hpc.tools/v2/public/plan/1276"
print(f"Fetching plan 1276 from: {url}\n")

try:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    data = response.json()
    
    print("="*60)
    print("PLAN 1276 API RESPONSE")
    print("="*60)
    print(json.dumps(data, indent=2))
    
    # Extract key fields
    print("\n" + "="*60)
    print("KEY FIELDS")
    print("="*60)
    
    plan_data = data.get("data", {})
    
    print(f"Plan ID: {plan_data.get('id')}")
    print(f"Requirements: {plan_data.get('requirements')}")
    print(f"Current Requirements: {plan_data.get('currentRequirements')}")
    print(f"Total Requirements: {plan_data.get('totalRequirements')}")
    print(f"Funding: {plan_data.get('funding')}")
    print(f"Total Funding: {plan_data.get('totalFunding')}")
    print(f"Current Funding: {plan_data.get('currentFunding')}")
    
    # Check planVersion
    pv = plan_data.get('planVersion', {})
    print(f"\nPlan Version:")
    print(f"  Name: {pv.get('name')}")
    print(f"  Code: {pv.get('code')}")
    print(f"  Start Date: {pv.get('startDate')}")
    print(f"  End Date: {pv.get('endDate')}")
    
    # List all top-level keys
    print(f"\nAll top-level keys in plan data:")
    for key in sorted(plan_data.keys()):
        print(f"  - {key}")
        
except Exception as e:
    print(f"Error fetching plan: {e}")
