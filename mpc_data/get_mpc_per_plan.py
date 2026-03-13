"""
MPC Requirements and Funding per Plan 2020-2026
Extracts data for multiple years matching https://fts.unocha.org/global-sectors/16/summary/[YEAR]

Uses the globalCluster grouping endpoint to capture MPC data regardless of
what a plan calls its local cluster (e.g. '3RP Basic Needs' maps to global
cluster 16 = Multipurpose Cash).

API structure (fts/flow?planId={id}&groupby=globalCluster):
  data.requirements.objects[]           → { id, name, origRequirements, revisedRequirements }
  data.report3.fundingTotals
      .singleFundingObjects[]           → { id, name, totalFunding, type, direction }
      .objectsBreakdown[]              → { id, name, totalFunding, singleFunding, sharedFunding }

  MPC may appear in singleFundingObjects but NOT in objectsBreakdown,
  so we check both and prefer whichever has the data.
"""

import requests
import pandas as pd
from datetime import datetime
from pathlib import Path
import time


# API Configuration
BASE_URL = "https://api.hpc.tools/v1/public"
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


def get_mpc_data_from_global_cluster(plan_id, debug=False):
    """Get MPC requirements and funding from the globalCluster grouping.

    This is the authoritative source — it catches plans where the local
    cluster is named something other than 'Multipurpose Cash' (e.g.
    'Basic Needs' in the Syria 3RP) but is mapped to global cluster 16
    (MPC) by FTS.

    Returns:
        dict: {'requirements': float or None, 'funded': float or None}
    """
    try:
        url = f"{FTS_ENDPOINT}?planId={plan_id}&groupby=globalCluster"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        result = {'requirements': None, 'funded': None}

        # --- REQUIREMENTS ---
        # Live in data.requirements.objects[] with id directly on the object
        req_objects = data.get('data', {}).get('requirements', {}).get('objects', [])
        for obj in req_objects:
            if obj.get('id') == MPC_CLUSTER_ID:
                # Prefer revisedRequirements, fall back to origRequirements
                result['requirements'] = obj.get('revisedRequirements') or obj.get('origRequirements')
                if debug:
                    print(f"      [DEBUG] Found MPC requirements: "
                          f"revised={obj.get('revisedRequirements')}, "
                          f"orig={obj.get('origRequirements')}")
                break

        # --- FUNDING ---
        # Can appear in two places within report3.fundingTotals:
        #   1. singleFundingObjects[] — for funding not shared across clusters
        #   2. objectsBreakdown[] — for the full breakdown including shared
        # MPC sometimes only appears in singleFundingObjects (e.g. Syria 3RP),
        # so we check both and take whichever has data.
        report3 = data.get('data', {}).get('report3', {}).get('fundingTotals', {})

        # Check singleFundingObjects first (most common location for MPC)
        for obj in report3.get('singleFundingObjects', []):
            if obj.get('id') == MPC_CLUSTER_ID:
                result['funded'] = obj.get('totalFunding')
                if debug:
                    print(f"      [DEBUG] Found MPC funding in singleFundingObjects: {result['funded']}")
                break

        # If not found there, check objectsBreakdown
        if result['funded'] is None:
            for obj in report3.get('objectsBreakdown', []):
                if obj.get('id') == MPC_CLUSTER_ID:
                    result['funded'] = obj.get('totalFunding')
                    if debug:
                        print(f"      [DEBUG] Found MPC funding in objectsBreakdown: {result['funded']}")
                    break

        # Clean up: treat zero as None
        if result['requirements'] is not None and result['requirements'] <= 0:
            result['requirements'] = None
        if result['funded'] is not None and result['funded'] <= 0:
            result['funded'] = None

        return result

    except requests.exceptions.RequestException as e:
        print(f"      [!] API error for plan {plan_id}: {e}")
        return {'requirements': None, 'funded': None}


def extract_mpc_data_for_year(year):
    """Extract MPC requirements and funding for all plans in a specific year"""

    print(f"\n{'='*70}")
    print(f"Processing Year: {year}")
    print(f"{'='*70}")

    # Get all plans for the year
    plans = get_plans(year)
    print(f"   [OK] Found {len(plans)} plans for {year}\n")

    results = []

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
            print(f"   [{i}/{len(plans)}] {plan_name[:60]}...")

        # Debug mode for first plan of each year to verify structure
        debug_mode = (i == 1)
        mpc_data = get_mpc_data_from_global_cluster(plan_id, debug=debug_mode)
        mpc_requirements = mpc_data.get('requirements')
        mpc_funding = mpc_data.get('funded')

        # Only include plans that have some MPC data
        if mpc_requirements or mpc_funding:
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

        # Small delay to be kind to the API
        time.sleep(0.1)

    print(f"\n   [OK] Found {len(results)} plans with MPC data for {year}")

    return results


def save_to_csv(data, combined=True):
    """Save data to CSV with timestamp"""
    if not data:
        print("\n   [X] No MPC data to save")
        return None

    df = pd.DataFrame(data)

    # Sort by year and requirements descending
    df = df.sort_values(['year', 'mpc_requirements_usd'], ascending=[True, False], na_position='last')

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    files_saved = []

    if combined:
        filename = f"mpc_requirements_funding_2020_2026_{timestamp}.csv"
        filepath = OUTPUT_DIR / filename
        df.to_csv(filepath, index=False)
        files_saved.append(filepath)

        total_requirements = df['mpc_requirements_usd'].sum()
        total_funded = df['mpc_funded_usd'].sum()
        overall_pct = (total_funded / total_requirements * 100) if total_requirements > 0 else 0

        print(f"\n{'=' * 70}")
        print(f"[SUCCESS] Combined data saved to: {filepath}")
        print(f"\nOVERALL SUMMARY (2020-2026):")
        print(f"  Total plans with MPC data: {len(df)}")
        print(f"  Total MPC Requirements: ${total_requirements:,.0f}")
        print(f"  Total MPC Funded:       ${total_funded:,.0f}")
        print(f"  Overall Funding %:      {overall_pct:.1f}%")
        print(f"  Unfunded:               ${(total_requirements - total_funded):,.0f}")

        print(f"\nYEAR-BY-YEAR SUMMARY:")
        print(f"{'-' * 70}")
        for year in sorted(df['year'].unique()):
            year_df = df[df['year'] == year]
            year_req = year_df['mpc_requirements_usd'].sum()
            year_funded = year_df['mpc_funded_usd'].sum()
            year_pct = (year_funded / year_req * 100) if year_req > 0 else 0
            print(f"  {year}: {len(year_df):>3} plans | "
                  f"Req: ${year_req:>16,.0f} | "
                  f"Funded: ${year_funded:>16,.0f} | "
                  f"{year_pct:>5.1f}%")

        print(f"{'=' * 70}\n")

    # Save individual year files
    print("Saving individual year files...")
    for year in sorted(df['year'].unique()):
        year_df = df[df['year'] == year]
        year_filename = f"mpc_requirements_funding_{year}_{timestamp}.csv"
        year_filepath = OUTPUT_DIR / year_filename
        year_df.to_csv(year_filepath, index=False)
        files_saved.append(year_filepath)
        print(f"  Saved {year}: {len(year_df)} plans -> {year_filename}")

    return files_saved


def main():
    """Main execution"""
    print("\n" + "=" * 70)
    print(">> MPC REQUIREMENTS AND FUNDING 2020-2026")
    print("   Source: FTS globalCluster grouping (cluster 16)")
    print("   Matching: https://fts.unocha.org/global-sectors/16/summary/[YEAR]")
    print("   Processing years: " + ", ".join(map(str, YEARS)))
    print("=" * 70 + "\n")

    all_data = []

    for year in YEARS:
        try:
            year_data = extract_mpc_data_for_year(year)
            all_data.extend(year_data)
        except Exception as e:
            print(f"\n[ERROR] Failed to process year {year}: {e}")
            import traceback
            traceback.print_exc()
            continue

    if all_data:
        save_to_csv(all_data, combined=True)
    else:
        print("\n[ERROR] No MPC data collected for any year")


if __name__ == "__main__":
    main()
