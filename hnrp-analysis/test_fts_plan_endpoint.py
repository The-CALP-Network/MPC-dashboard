"""
Test different FTS endpoints to find the correct way to get plan funding
According to FTS website, plan 1276 should have funding of $1,183,792,196
"""

# Since requests might not be available, let's document the correct API approach

print("""
FINDING THE RIGHT API ENDPOINT FOR PLAN FUNDING
================================================

Based on the FTS documentation and the image provided, plan 1276 (Syrian Arab Republic 2025)
should show:
- Total funding: $2,554,454,402
- Funded through this plan: $1,183,792,196
- Outside this plan: $1,370,662,206

The correct endpoints to try:

1. FTS Plan Summary endpoint:
   https://api.hpc.tools/v1/public/fts/plan/summary/{year}/{planId}
   Example: https://api.hpc.tools/v1/public/fts/plan/summary/2025/1276

2. FTS Flow endpoint filtered by plan:
   https://api.hpc.tools/v1/public/fts/flow?planId={planId}&year={year}
   Example: https://api.hpc.tools/v1/public/fts/flow?planId=1276&year=2025

3. HPC Plan API with embedded funding:
   https://api.hpc.tools/v2/public/plan/{planId}
   Example: https://api.hpc.tools/v2/public/plan/1276

The issue with the current script:
- It's trying to parse all flows and match them to plans by looking at destinationObjects
- This is fragile and may miss flows or miscount them
- Better approach: use planId as a query parameter to get all flows for that specific plan

RECOMMENDED FIX:
Instead of fetching ALL flows and trying to match them, fetch flows per plan using:
https://api.hpc.tools/v1/public/fts/flow?planId={planId}&year={year}

Then sum up the amountUSD for all returned flows.
""")

# Show the code pattern that should work
print("\n\nRECOMMENDED CODE PATTERN:")
print("="*60)

code_example = '''
def get_plan_funding(plan_id, year):
    """Get total funding for a specific plan"""
    url = f"https://api.hpc.tools/v1/public/fts/flow?planId={plan_id}&year={year}"
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    
    flows = data.get('data', {}).get('flows', [])
    total_funding = sum(flow.get('amountUSD', 0) for flow in flows)
    
    return total_funding

# Then in process_year():
for plan in hpc_plans:
    # ... extract plan info ...
    plan_id = plan.get('id')
    funded_usd = get_plan_funding(plan_id, year)
    
    rows.append({
        # ... other fields ...
        "funded_usd": funded_usd,
    })
'''

print(code_example)
print("="*60)
