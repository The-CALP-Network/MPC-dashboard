"""
Quick test to verify the fix for plan 1276 funding
"""
import requests

def get_plan_funding(plan_id, year):
    """
    Get total funding for a specific plan using fundingTotal from API summary
    """
    try:
        url = f"https://api.hpc.tools/v1/public/fts/flow"
        params = {"planId": plan_id, "year": year}
        
        response = requests.get(url, params=params, timeout=(10, 60))
        response.raise_for_status()

        # NEW (CORRECT) - Uses pre-calculated total
        data = response.json().get('data', {})
        incoming = data.get('incoming', {})
        funding_total = incoming.get('fundingTotal', 0)
        
        return funding_total
        
    except Exception as e:
        print(f"Error fetching funding for plan {plan_id}: {e}")
        return None


# Test with Syrian Arab Republic plan 1276 for 2025
plan_id = 1276
year = 2025

print(f"Testing funding fetch for plan {plan_id} ({year})...")
funding = get_plan_funding(plan_id, year)

if funding:
    funding_m = funding / 1_000_000
    print(f"\n✓ SUCCESS!")
    print(f"Plan {plan_id} total funding: ${funding:,.0f}")
    print(f"Plan {plan_id} total funding: ${funding_m:.2f}M")
    print(f"\nExpected: ~$1,183.79M (or $1.18bn)")
    print(f"Match: {'YES ✓' if abs(funding_m - 1183.79) < 1 else 'NO ✗'}")
else:
    print("✗ FAILED - No funding data returned")

