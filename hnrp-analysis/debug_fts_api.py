import requests
import json

# Check the FTS API structure for 2025
print("Fetching FTS flows for 2025...")
url = "https://api.hpc.tools/v1/public/fts/flow?year=2025&limit=10"
response = requests.get(url)
data = response.json()

print(f"\nTotal flows in response: {data['data']['count']}")
print(f"\nShowing first flow structure:\n")

if data['data']['flows']:
    flow = data['data']['flows'][0]
    print(json.dumps(flow, indent=2))
    
print("\n" + "="*60)
print("Looking for flows linked to plan 1276 (Syrian Arab Republic)")
print("="*60)

# Fetch more flows to find plan 1276
url_full = "https://api.hpc.tools/v1/public/fts/flow?year=2025&limit=100"
response = requests.get(url_full)
data = response.json()

plan_1276_flows = []
for flow in data['data']['flows']:
    # Check all possible locations for plan references
    dest_objects = flow.get('destinationObjects', [])
    source_objects = flow.get('sourceObjects', [])
    
    all_objects = dest_objects + source_objects
    
    for obj in all_objects:
        if obj.get('id') == 1276 or (isinstance(obj.get('id'), str) and obj.get('id') == '1276'):
            plan_1276_flows.append(flow)
            break

if plan_1276_flows:
    print(f"\nFound {len(plan_1276_flows)} flows for plan 1276")
    print("\nFirst flow structure:")
    print(json.dumps(plan_1276_flows[0], indent=2))
else:
    print("\nNo flows found for plan 1276 in first 100 flows")
    print("\nLet's check the plan summary API instead:")
    
    plan_url = "https://api.hpc.tools/v2/public/plan/1276"
    plan_response = requests.get(plan_url)
    plan_data = plan_response.json()
    
    print(f"\nPlan data:")
    print(json.dumps(plan_data, indent=2))
