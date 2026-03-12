"""
MPC Requirements and Funding per Plan 2020-2026
Extracts data for multiple years matching https://fts.unocha.org/global-sectors/16/summary/[YEAR]
"""

import requests
import pandas as pd
from datetime import datetime
from pathlib import Path


# API Configuration
BASE_URL = "https://api.hpc.tools/v1/public"
MPC_ENDPOINT = f"{BASE_URL}/governingEntity"
FTS_ENDPOINT = f"{BASE_URL}/fts/flow"

# Multipurpose Cash Cluster ID
MPC_CLUSTER_ID = 16

# Years to process
YEARS = [2020, 2021, 2022, 2023, 2024, 2025, 2026]

# Output directory
OUTPUT_DIR = Path(r"C:\Users\rcrew\CALP\CALP - 100 Python working folder\hnrp-analysis\mpc_data")


def get_plans(year):
    """Fetch all plans for a specific year"""
    print(f"   Fetching {year} plans...")
    plans_endpoint = f"{BASE_URL}/rpm/plan/year/{year}"
    response = requests.get(plans_endpoint)
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
        # Silently handle errors to avoid excessive output
        return None


def get_mpc_funding(plan_id):
    """Get MPC funding flows for a plan where globalClusterId = 16"""
    try:
        url = f"{FTS_ENDPOINT}?globalClusterId={MPC_CLUSTER_ID}&planId={plan_id}"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        # Use fundingTotal from incoming summary instead of summing flows (which only returns first page)
        incoming = data.get('data', {}).get('incoming', {})
        total_funding = incoming.get('fundingTotal', 0)
        
        return total_funding if total_funding > 0 else None
        
    except Exception as e:
        # Silently handle errors to avoid excessive output
        return None


def extract_mpc_data_for_year(year):
    """Extract MPC requirements and funding for all plans in a specific year"""
    
    print(f"\n{'='*70}")
    print(f"Processing Year: {year}")
    print(f"{'='*70}")
    
    # Get all plans for the year
    plans = get_plans(year)
    print(f"   [OK] Found {len(plans)} plans for {year}\n")
    
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
        
        if i % 10 == 0 or i == len(plans):
            print(f"   [{i}/{len(plans)}] Processing {plan_name}...")
        
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
                'year': year,
                'plan_id': plan_id,
                'plan_name': plan_name,
                'plan_type': plan_type,
                'country': country,
                'mpc_requirements_usd': mpc_requirements,
                'mpc_funded_usd': mpc_funding,
                'percent_funded': pct_funded,
                'unfunded_usd': (mpc_requirements - mpc_funding) if (mpc_requirements and mpc_funding) else None
            })
    
    print(f"\n   [OK] Found {len(results)} plans with MPC data for {year}")
    
    return results


def save_to_csv(data, combined=True):
    """Save data to CSV with timestamp"""
    if not data:
        print("\n   [X] No MPC data to save")
        return None
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    # Sort by year and requirements descending
    df = df.sort_values(['year', 'mpc_requirements_usd'], ascending=[True, False], na_position='last')
    
    # Create timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Ensure data directory exists
    data_dir = OUTPUT_DIR
    data_dir.mkdir(parents=True, exist_ok=True)
    
    files_saved = []
    
    if combined:
        # Save combined file
        filename = f"mpc_requirements_funding_2020_2026_{timestamp}.csv"
        filepath = data_dir / filename
        df.to_csv(filepath, index=False)
        files_saved.append(filepath)
        
        # Calculate totals
        total_requirements = df['mpc_requirements_usd'].sum()
        total_funded = df['mpc_funded_usd'].sum()
        overall_pct = (total_funded / total_requirements * 100) if total_requirements > 0 else 0
        
        print(f"\n{'=' * 70}")
        print(f"[SUCCESS] Combined data saved to: {filepath}")
        print(f"\nOVERALL SUMMARY (2020-2026):")
        print(f"  Total plans with MPC data: {len(df)}")
        print(f"  Total MPC Requirements: ${total_requirements:,.0f}")
        print(f"  Total MPC Funded: ${total_funded:,.0f}")
        print(f"  Overall Funding %: {overall_pct:.1f}%")
        print(f"  Unfunded: ${(total_requirements - total_funded):,.0f}")
        
        # Print year-by-year summary
        print(f"\nYEAR-BY-YEAR SUMMARY:")
        print(f"{'-' * 70}")
        for year in sorted(df['year'].unique()):
            year_df = df[df['year'] == year]
            year_req = year_df['mpc_requirements_usd'].sum()
            year_funded = year_df['mpc_funded_usd'].sum()
            year_pct = (year_funded / year_req * 100) if year_req > 0 else 0
            print(f"  {year}: {len(year_df)} plans | Req: ${year_req:,.0f} | Funded: ${year_funded:,.0f} | {year_pct:.1f}%")
        
        print(f"{'=' * 70}\n")
    
    # Also save individual year files
    print("Saving individual year files...")
    for year in sorted(df['year'].unique()):
        year_df = df[df['year'] == year]
        year_filename = f"mpc_requirements_funding_{year}_{timestamp}.csv"
        year_filepath = data_dir / year_filename
        year_df.to_csv(year_filepath, index=False)
        files_saved.append(year_filepath)
        print(f"  ✓ Saved {year} data to: {year_filename}")
    
    return files_saved


def main():
    """Main execution"""
    print("\n" + "=" * 70)
    print(">> MPC REQUIREMENTS AND FUNDING 2020-2026")
    print("   Processing data for years: " + ", ".join(map(str, YEARS)))
    print("=" * 70 + "\n")
    
    all_data = []
    
    # Process each year
    for year in YEARS:
        try:
            year_data = extract_mpc_data_for_year(year)
            all_data.extend(year_data)
        except Exception as e:
            print(f"\n[ERROR] Failed to process year {year}: {e}")
            continue
    
    # Save to CSV
    if all_data:
        save_to_csv(all_data, combined=True)
    else:
        print("\n[ERROR] No MPC data collected for any year")


if __name__ == "__main__":
    main()
