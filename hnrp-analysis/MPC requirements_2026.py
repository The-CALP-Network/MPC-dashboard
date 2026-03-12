"""
MPC Requirements and Funding per Plan 2026
Extracts data matching https://fts.unocha.org/global-sectors/16/summary/2026
"""

import requests
import pandas as pd
from datetime import datetime
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
    print("   Fetching 2026 plans...")
    response = requests.get(PLANS_ENDPOINT)
    response.raise_for_status()
    return response.json().get('data', [])


def get_mpc_requirements(plan_id):
    """Get MPC requirements (cost) for a plan where globalClusterId = 16"""
    try:
        url = f"{MPC_ENDPOINT}?planId={plan_id}"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        total_mpc_cost = 0
        entities = data.get('data', [])
        
        # Find entities with globalClusterId = 16
        for entity in entities:
            cluster_ids = entity.get('globalClusterIds', [])
            if MPC_CLUSTER_ID in cluster_ids:
                # Extract cost from attachments
                attachments = entity.get('attachments', [])
                for attachment in attachments:
                    if attachment.get('type') == 'cost':
                        att_version = attachment.get('attachmentVersion', {})
                        att_value = att_version.get('value', {})
                        cost = att_value.get('cost', 0)
                        if cost:
                            total_mpc_cost += cost
        
        return total_mpc_cost if total_mpc_cost > 0 else None
        
    except Exception as e:
        print(f"   [!] Error getting MPC requirements for plan {plan_id}: {e}")
        return None


def get_mpc_funding(plan_id):
    """Get MPC funding flows for a plan where globalClusterId = 16"""
    try:
        url = f"{FTS_ENDPOINT}?globalClusterId={MPC_CLUSTER_ID}&planId={plan_id}"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        # Sum all funding flows
        flows = data.get('data', {}).get('flows', [])
        total_funding = sum(flow.get('amountUSD', 0) for flow in flows)
        
        return total_funding if total_funding > 0 else None
        
    except Exception as e:
        print(f"   [!] Error getting MPC funding for plan {plan_id}: {e}")
        return None


def extract_mpc_data():
    """Extract MPC requirements and funding for all 2026 plans"""
    
    # Get all plans
    plans = get_plans()
    print(f"   [OK] Found {len(plans)} plans\n")
    
    results = []
    
    print("   Processing plans...\n")
    
    for i, plan in enumerate(plans, 1):
        plan_id = plan.get('id')
        plan_version = plan.get('planVersion', {})
        plan_name = plan_version.get('name', 'Unknown')
        
        # Get plan type
        plan_type = ''
        if plan.get('categories') and len(plan.get('categories', [])) > 0:
            plan_type = plan['categories'][0].get('name', '')
        
        # Get country
        country = ''
        if plan.get('locations') and len(plan.get('locations', [])) > 0:
            country = plan['locations'][0].get('name', '')
        
        print(f"   [{i}/{len(plans)}] {plan_name}")
        
        # Get MPC requirements
        mpc_requirements = get_mpc_requirements(plan_id)
        
        # Get MPC funding
        mpc_funding = get_mpc_funding(plan_id)
        
        # Only add if there's MPC data
        if mpc_requirements or mpc_funding:
            # Calculate percentage funded
            pct_funded = None
            if mpc_requirements and mpc_funding and mpc_requirements > 0:
                pct_funded = (mpc_funding / mpc_requirements) * 100
            
            results.append({
                'plan_id': plan_id,
                'plan_name': plan_name,
                'plan_type': plan_type,
                'country': country,
                'mpc_requirements_usd': mpc_requirements,
                'mpc_funded_usd': mpc_funding,
                'percent_funded': pct_funded,
                'unfunded_usd': (mpc_requirements - mpc_funding) if (mpc_requirements and mpc_funding) else None
            })
            print(f"        Req: ${mpc_requirements:,.0f} | Funded: ${mpc_funding:,.0f}" if mpc_requirements and mpc_funding else f"        Req: ${mpc_requirements:,.0f}" if mpc_requirements else f"        Funded: ${mpc_funding:,.0f}")
        else:
            print(f"        No MPC data")
    
    return results


def save_to_csv(data):
    """Save data to CSV with timestamp"""
    if not data:
        print("\n   [X] No MPC data to save")
        return None
    
    # Create timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"mpc_requirements_funding_2026_{timestamp}.csv"
    filepath = Path("data") / filename
    
    # Ensure data directory exists
    filepath.parent.mkdir(exist_ok=True)
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    # Sort by requirements descending
    df = df.sort_values('mpc_requirements_usd', ascending=False, na_position='last')
    
    # Save to CSV
    df.to_csv(filepath, index=False)
    
    # Calculate totals
    total_requirements = df['mpc_requirements_usd'].sum()
    total_funded = df['mpc_funded_usd'].sum()
    overall_pct = (total_funded / total_requirements * 100) if total_requirements > 0 else 0
    
    print(f"\n{'=' * 70}")
    print(f"[SUCCESS] Data saved to: {filepath}")
    print(f"\nSUMMARY:")
    print(f"  Plans with MPC data: {len(df)}")
    print(f"  Total MPC Requirements: ${total_requirements:,.0f}")
    print(f"  Total MPC Funded: ${total_funded:,.0f}")
    print(f"  Overall Funding %: {overall_pct:.1f}%")
    print(f"  Unfunded: ${(total_requirements - total_funded):,.0f}")
    print(f"{'=' * 70}\n")
    
    return filepath


def main():
    """Main execution"""
    print("\n" + "=" * 70)
    print(">> MPC REQUIREMENTS AND FUNDING 2026")
    print("   Matching: https://fts.unocha.org/global-sectors/16/summary/2026")
    print("=" * 70 + "\n")
    
    # Extract data
    data = extract_mpc_data()
    
    # Save to CSV
    save_to_csv(data)


if __name__ == "__main__":
    main()
