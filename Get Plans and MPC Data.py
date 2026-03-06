"""
HNRP Analysis - MPCA Requirements Data Extractor
Pulls plans and MPC data from HPC Tools API and exports to CSV
"""

import requests
import json
from datetime import datetime
import pandas as pd
from pathlib import Path


# API Configuration
BASE_URL = "https://api.hpc.tools/v1/public"
PLANS_ENDPOINT = f"{BASE_URL}/rpm/plan/year/2026"
MPC_ENDPOINT = f"{BASE_URL}/governingEntity"
FTS_ENDPOINT = f"{BASE_URL}/fts/flow"

# Multipurpose Cash Cluster ID
MPC_CLUSTER_ID = 16


def get_plans():
    """Fetch all plans for 2026"""
    try:
        print("   Making request to:", PLANS_ENDPOINT)
        response = requests.get(PLANS_ENDPOINT)
        response.raise_for_status()
        data = response.json()
        return data.get('data', [])
    except requests.exceptions.RequestException as e:
        print(f"   [X] Error fetching plans: {e}")
        return []


def get_mpc_data(plan_id):
    """Fetch MPC data for a specific plan"""
    try:
        url = f"{MPC_ENDPOINT}?planId={plan_id}"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"   [!] Error fetching MPC data for plan {plan_id}: {e}")
        return None


def get_funding_flows(plan_id):
    """Fetch FTS funding flows for MPC (globalClusterId=16) for a specific plan"""
    try:
        url = f"{FTS_ENDPOINT}?globalClusterId={MPC_CLUSTER_ID}&planId={plan_id}"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        # Sum all funding flows
        flows = data.get('data', {}).get('flows', [])
        total_funding = sum(flow.get('amountUSD', 0) for flow in flows)
        return total_funding
    except requests.exceptions.RequestException as e:
        print(f"   [!] Error fetching funding flows for plan {plan_id}: {e}")
        return None


def flatten_mpc_data(plans, mpc_responses, funding_flows):
    """
    Flatten nested JSON data into CSV-friendly format
    Filters for ONLY multipurpose cash (globalClusterId=16)
    Extracts: origRequirements, MPC requirements, MPC people targeted, MPC funding flows
    """
    flattened_data = []
    
    for plan in plans:
        plan_id = plan.get('id')
        plan_name = plan.get('planVersion', {}).get('name', 'Unknown')
        
        # Get plan metadata
        country = ''
        if plan.get('locations') and len(plan.get('locations', [])) > 0:
            country = plan['locations'][0].get('name', '')
        
        plan_type = ''
        if plan.get('categories') and len(plan.get('categories', [])) > 0:
            plan_type = plan['categories'][0].get('name', '')
        
        # Extract origRequirements from plan
        orig_requirements = None
        plan_version = plan.get('planVersion', {})
        requirements = plan_version.get('requirements', [])
        for req in requirements:
            if req.get('versionAttachments'):
                for va in req['versionAttachments']:
                    if va.get('type') == 'origRequirements':
                        orig_requirements = va.get('value')
                        break
        
        mpc_data = mpc_responses.get(plan_id)
        
        if not mpc_data:
            # No MPC data for this plan - skip it
            continue
            
        # Extract MPC details - FILTER FOR CLUSTER ID 16 ONLY
        mpc_results = mpc_data.get('data', [])
        
        if not mpc_results:
            # No MPC records - skip
            continue
        
        for mpc in mpc_results:
            # Check if this MPC has globalClusterId = 16
            cluster_ids = mpc.get('globalClusterIds', [])
            
            # FILTER: Only include if cluster ID 16 is present
            if MPC_CLUSTER_ID not in cluster_ids:
                continue
            
            row = {
                'plan_id': plan_id,
                'plan_name': plan_name,
                'country': country,
                'plan_type': plan_type,
                'orig_requirements': orig_requirements,
                'mpc_name': '',
                'mpc_requirements_cost': None,
                'mpc_people_targeted': None,
                'mpc_funding_flows_usd': funding_flows.get(plan_id),
            }
            
            # Extract MPC name
            if mpc.get('governingEntityVersion'):
                row['mpc_name'] = mpc['governingEntityVersion'].get('name', '')
            
            # Extract cost data and people targeted from attachments
            attachments = mpc.get('attachments', [])
            for attachment in attachments:
                att_type = attachment.get('type')
                
                if att_type == 'cost':
                    # MPC requirements cost
                    att_version = attachment.get('attachmentVersion', {})
                    att_value = att_version.get('value', {})
                    row['mpc_requirements_cost'] = att_value.get('cost')
                    
                elif att_type == 'caseLoad':
                    # MPC people targeted
                    att_version = attachment.get('attachmentVersion', {})
                    att_value = att_version.get('value', {})
                    metrics = att_value.get('metrics', {})
                    values = metrics.get('values', {})
                    totals = values.get('totals', [])
                    for total in totals:
                        if total.get('type') == 'target':
                            row['mpc_people_targeted'] = total.get('value')
                            break
            
            flattened_data.append(row)
    
    return flattened_data


def save_to_csv(data, base_filename):
    """Save data to CSV with timestamp"""
    if not data:
        print("   [X] No data to save")
        return None
    
    # Create timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{base_filename}_{timestamp}.csv"
    filepath = Path("data") / filename
    
    # Ensure data directory exists
    filepath.parent.mkdir(exist_ok=True)
    
    # Save using pandas for better handling
    df = pd.DataFrame(data)
    df.to_csv(filepath, index=False)
    print(f"   [OK] Data saved to: {filepath}")
    return filepath


def main():
    """Main execution flow"""
    print("\n" + "=" * 70)
    print(">> HNRP ANALYSIS - MPCA REQUIREMENTS DATA EXTRACTION")
    print("=" * 70)
    
    # Step 1: Get all plans
    print("\n[Step 1] Fetching plans for 2026...")
    plans = get_plans()
    print(f"   [OK] Found {len(plans)} plans")
    
    if not plans:
        print("   [X] No plans found. Exiting.")
        return
    
    # Step 2: Get MPC data for each plan
    print(f"\n[Step 2] Fetching MPC data for {len(plans)} plans...")
    mpc_responses = {}
    
    for i, plan in enumerate(plans, 1):
        plan_id = plan.get('id')
        plan_name = plan.get('planVersion', {}).get('name', 'Unknown')
        print(f"   [{i}/{len(plans)}] {plan_name} (ID: {plan_id})")
        
        mpc_data = get_mpc_data(plan_id)
        if mpc_data:
            mpc_responses[plan_id] = mpc_data
    
    print(f"   [OK] Retrieved MPC data for {len(mpc_responses)} plans")
    
    # Step 3: Get funding flows for each plan
    print(f"\n[Step 3] Fetching funding flows for {len(plans)} plans...")
    funding_flows = {}
    
    for i, plan in enumerate(plans, 1):
        plan_id = plan.get('id')
        funding = get_funding_flows(plan_id)
        if funding is not None:
            funding_flows[plan_id] = funding
    
    print(f"   [OK] Retrieved funding data for {len(funding_flows)} plans")
    
    # Step 4: Flatten and combine data (filter for MPC cluster ID 16 only)
    print("\n[Step 4] Processing and flattening MPC data (globalClusterId=16)...")
    flattened_data = flatten_mpc_data(plans, mpc_responses, funding_flows)
    print(f"   [OK] Processed {len(flattened_data)} MPC records")
    
    # Step 5: Save to CSV
    print("\n[Step 5] Saving to CSV...")
    filepath = save_to_csv(flattened_data, "mpca_requirements")
    
    print("\n" + "=" * 70)
    print("[SUCCESS] EXTRACTION COMPLETE!")
    if filepath:
        print(f"Output file: {filepath}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
