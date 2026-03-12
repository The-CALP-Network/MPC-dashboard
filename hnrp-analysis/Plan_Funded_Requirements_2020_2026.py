import requests
import pandas as pd
from collections import defaultdict
from pathlib import Path

HPC_URL = "https://api.hpc.tools/v2/public/plan"

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "python-requests"
}

# Years to process
YEARS = [2020, 2021, 2022, 2023, 2024, 2025, 2026]

# Output directory
OUTPUT_DIR = Path(r"C:\Users\rcrew\CALP\CALP - 100 Python working folder\hnrp-analysis\plan_data")


def fetch_json(url, params=None, timeout=(10, 120)):
    r = requests.get(url, params=params, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    return r.json()


def safe_get(d, key, default=None):
    return d.get(key, default) if isinstance(d, dict) else default


def to_number(x):
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        x = x.replace(",", "").replace("$", "").replace("%", "").strip()
        try:
            return float(x)
        except ValueError:
            return None
    return None


def extract_year(plan_version):
    start_date = safe_get(plan_version, "startDate")
    if start_date:
        return int(str(start_date)[:4])
    return None


def classify_plan(code):
    if pd.isna(code):
        return "Other"
    if code.startswith("H"):
        return "Country humanitarian"
    if code.startswith("R"):
        return "Regional"
    if code.startswith("F"):
        return "Flash appeal"
    if code.startswith("O"):
        return "Global overview"
    return "Other"


def extract_requirements(plan):
    candidates = [
        "requirements",
        "currentRequirement",
        "currentRequirements",
        "totalRequirements",
        "financialRequirements",
        "revisedRequirements",
    ]

    for key in candidates:
        if key in plan and plan[key] not in (None, ""):
            return plan[key]

    pv = safe_get(plan, "planVersion", {})
    for key in candidates:
        if key in pv and pv[key] not in (None, ""):
            return pv[key]

    return None


def get_plan_funding(plan_id, year):
    """
    Get total funding for a specific plan by querying FTS flows with planId parameter.
    Uses the fundingTotal from the API summary instead of paginating through all flows.
    """
    try:
        url = f"https://api.hpc.tools/v1/public/fts/flow"
        params = {"planId": plan_id, "year": year}
        
        response = fetch_json(url, params=params, timeout=(10, 60))
        
        # Use the fundingTotal from the summary instead of iterating through paginated flows
        data = response.get('data', {})
        incoming = data.get('incoming', {})
        funding_total = incoming.get('fundingTotal', 0)
        
        return funding_total if funding_total > 0 else None
        
    except Exception as e:
        print(f"   [!] Error fetching funding for plan {plan_id}: {e}")
        return None





def process_year(year):
    """
    Process HPC plans for a specific year and fetch funding from FTS using planId parameter
    """
    print(f"\n{'='*60}")
    print(f"Processing Year: {year}")
    print(f"{'='*60}")
    
    print(f"Fetching HPC plans for {year}...")
    hpc_payload = fetch_json(HPC_URL, params={"limit": 5000}, timeout=(10, 60))
    hpc_plans = hpc_payload["data"]

    # First pass: collect all plans for the year
    year_plans = []
    for plan in hpc_plans:
        pv = safe_get(plan, "planVersion", {})
        plan_year = extract_year(pv)

        if plan_year != year:
            continue

        year_plans.append(plan)

    print(f"Found {len(year_plans)} plans for {year}")
    print(f"Fetching funding data for each plan...")

    # Second pass: get funding for each plan
    rows = []
    for i, plan in enumerate(year_plans, 1):
        pv = safe_get(plan, "planVersion", {})
        code = safe_get(pv, "code")
        plan_id = safe_get(plan, "id")
        plan_name = safe_get(pv, "name")
        
        # Show progress for every 5 plans
        if i % 5 == 0 or i == len(year_plans):
            print(f"   [{i}/{len(year_plans)}] Processing {plan_name}...")
        
        # Get funding by querying FTS with planId parameter
        funded_usd = get_plan_funding(plan_id, year)

        rows.append({
            "year": year,
            "plan_id": plan_id,
            "plan_version_id": safe_get(pv, "id"),
            "plan_code": code,
            "plan_name": plan_name,
            "start_date": safe_get(pv, "startDate"),
            "end_date": safe_get(pv, "endDate"),
            "requirements_usd": to_number(extract_requirements(plan)),
            "funded_usd": funded_usd,
            "plan_group": classify_plan(code)
        })

    df_hpc = pd.DataFrame(rows).drop_duplicates()
    df_hpc["requirements_usd"] = pd.to_numeric(df_hpc["requirements_usd"], errors="coerce")
    df_hpc["funded_usd"] = pd.to_numeric(df_hpc["funded_usd"], errors="coerce")

    print(f"\n✓ Completed processing {len(df_hpc)} plans for {year}")
    
    # Calculate coverage and convert to millions
    df_hpc["coverage_pct"] = (
        df_hpc["funded_usd"] / df_hpc["requirements_usd"] * 100
    ).round(1)

    df_hpc["requirements_usd_m"] = (df_hpc["requirements_usd"] / 1_000_000).round(1)
    df_hpc["funded_usd_m"] = (df_hpc["funded_usd"] / 1_000_000).round(1)

    df_hpc = df_hpc.sort_values("requirements_usd", ascending=False)

    print(f"\nTop 10 plans by requirements for {year}:\n")
    print(df_hpc[['plan_name', 'requirements_usd_m', 'funded_usd_m', 'coverage_pct']].head(10).to_string(index=False))
    
    return df_hpc


def main():
    """
    Main function to process all years and combine results
    """
    print("="*60)
    print("HPC Plan Requirements and Funding: 2020-2026")
    print("="*60)
    
    all_dfs = []
    
    for year in YEARS:
        try:
            df_year = process_year(year)
            all_dfs.append(df_year)
        except Exception as e:
            print(f"\n[ERROR] Failed to process year {year}: {e}")
            continue
    
    # Combine all years
    if all_dfs:
        df_combined = pd.concat(all_dfs, ignore_index=True)
        df_combined = df_combined.sort_values(["year", "requirements_usd"], ascending=[True, False])
        
        # Ensure output directory exists
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        
        # Save combined data
        output_file = OUTPUT_DIR / "ocha_hpc_2020_2026_plan_requirements_and_funding.csv"
        df_combined.to_csv(output_file, index=False)
        
        print(f"\n{'='*60}")
        print(f"SUMMARY - All Years (2020-2026)")
        print(f"{'='*60}")
        print(f"Total plans: {len(df_combined)}")
        print(f"Total requirements: ${df_combined['requirements_usd'].sum():,.0f}")
        print(f"Total funded: ${df_combined['funded_usd'].sum():,.0f}")
        print(f"\nBreakdown by year:")
        summary = df_combined.groupby('year').agg({
            'plan_id': 'count',
            'requirements_usd': 'sum',
            'funded_usd': 'sum'
        }).rename(columns={'plan_id': 'plan_count'})
        summary['coverage_pct'] = (summary['funded_usd'] / summary['requirements_usd'] * 100).round(1)
        print(summary.to_string())
        
        print(f"\n✓ Saved combined data to {output_file}")
        
        # Save year-by-year files as well
        for year in YEARS:
            df_year = df_combined[df_combined['year'] == year]
            if not df_year.empty:
                year_file = OUTPUT_DIR / f"ocha_hpc_{year}_plan_requirements_and_funding.csv"
                df_year.to_csv(year_file, index=False)
                print(f"✓ Saved {year} data to {year_file.name}")
    else:
        print("\n[ERROR] No data was successfully processed.")


if __name__ == "__main__":
    main()
