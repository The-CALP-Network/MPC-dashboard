"""Debug script to inspect API response structure"""
import requests
import json

# Get first plan
plans_response = requests.get("https://api.hpc.tools/v1/public/rpm/plan/year/2026")
plans = plans_response.json().get('data', [])

if plans:
    # Get MPC data for first plan
    plan_id = plans[0]['id']
    plan_name = plans[0].get('planVersion', {}).get('name', 'Unknown')
    
    print(f"Inspecting: {plan_name} (ID: {plan_id})\n")
    print("=" * 70)
    
    mpc_response = requests.get(f"https://api.hpc.tools/v1/public/governingEntity?planId={plan_id}")
    mpc_data = mpc_response.json()
    
    # Print first MPC record structure
    if mpc_data.get('data'):
        print("\nFirst MPC record structure:\n")
        print(json.dumps(mpc_data['data'][0], indent=2))
    else:
        print("No MPC data found")
