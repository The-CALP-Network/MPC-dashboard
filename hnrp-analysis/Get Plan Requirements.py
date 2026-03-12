"""
Get USD Requirements per Plan for 2026
Simple script to extract financial requirements from HPC Tools API
"""

import requests
import pandas as pd
from datetime import datetime
from pathlib import Path


# API Configuration
BASE_URL = "https://api.hpc.tools/v1/public"
PLANS_ENDPOINT = f"{BASE_URL}/rpm/plan/year/2026"


def get_plan_requirements():
    """Fetch all plans for 2026 with their USD requirements"""
    try:
        print("Fetching plans from API...")
        response = requests.get(PLANS_ENDPOINT)
        response.raise_for_status()
        data = response.json()
        plans = data.get('data', [])
        
        print(f"Found {len(plans)} plans\n")
        
        plan_data = []
        
        for plan in plans:
            plan_id = plan.get('id')
            plan_version = plan.get('planVersion', {})
            plan_name = plan_version.get('name', 'Unknown')
            
            # Get location (country)
            country = ''
            if plan.get('locations') and len(plan.get('locations', [])) > 0:
                country = plan['locations'][0].get('name', '')
            
            # Get plan type/category
            plan_type = ''
            if plan.get('categories') and len(plan.get('categories', [])) > 0:
                plan_type = plan['categories'][0].get('name', '')
            
            # Extract requirements (origRequirements)
            requirements_usd = None
            requirements_list = plan_version.get('requirements', [])
            
            for req in requirements_list:
                version_attachments = req.get('versionAttachments', [])
                for attachment in version_attachments:
                    if attachment.get('type') == 'origRequirements':
                        requirements_usd = attachment.get('value')
                        break
                if requirements_usd is not None:
                    break
            
            plan_data.append({
                'plan_id': plan_id,
                'plan_name': plan_name,
                'country': country,
                'plan_type': plan_type,
                'requirements_usd': requirements_usd
            })
            
            print(f"  {plan_name}: ${requirements_usd:,}" if requirements_usd else f"  {plan_name}: No requirements data")
        
        return plan_data
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching plans: {e}")
        return []


def save_to_csv(data, base_filename):
    """Save data to CSV with timestamp"""
    if not data:
        print("\nNo data to save")
        return None
    
    # Create timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{base_filename}_{timestamp}.csv"
    filepath = Path("data") / filename
    
    # Ensure data directory exists
    filepath.parent.mkdir(exist_ok=True)
    
    # Save using pandas
    df = pd.DataFrame(data)
    
    # Calculate total
    total_requirements = df['requirements_usd'].sum()
    
    df.to_csv(filepath, index=False)
    print(f"\n{'=' * 70}")
    print(f"Data saved to: {filepath}")
    print(f"Total Plans: {len(df)}")
    print(f"Total Requirements (USD): ${total_requirements:,.0f}")
    print(f"{'=' * 70}\n")
    
    return filepath


def main():
    """Main execution flow"""
    print("\n" + "=" * 70)
    print(">> 2026 PLAN REQUIREMENTS EXTRACTION")
    print("=" * 70 + "\n")
    
    # Get plan requirements
    plan_data = get_plan_requirements()
    
    # Save to CSV
    save_to_csv(plan_data, "plan_requirements")


if __name__ == "__main__":
    main()
