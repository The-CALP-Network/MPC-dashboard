import requests
import pandas as pd

BASE_URL = "https://api.hpc.tools/v2/public/plan"
HEADERS = {
    "Accept": "application/json",
    "User-Agent": "python-requests"
}

def fetch_plans(limit=5000):
    r = requests.get(
        BASE_URL,
        params={"limit": limit},
        headers=HEADERS,
        timeout=(10, 60)
    )
    r.raise_for_status()
    payload = r.json()
    return payload["data"]

def safe_get(d, key, default=None):
    return d.get(key, default) if isinstance(d, dict) else default

def extract_year(plan_version):
    start_date = safe_get(plan_version, "startDate")
    if start_date:
        return int(str(start_date)[:4])
    code = safe_get(plan_version, "code", "")
    if len(code) >= 2:
        tail = code[-2:]
        if tail.isdigit():
            yy = int(tail)
            return 2000 + yy if yy <= 50 else 1900 + yy
    return None

def extract_requirements(plan):
    # Try likely locations
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

def to_number(x):
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return x
    if isinstance(x, str):
        x = x.replace(",", "").replace("$", "").strip()
        try:
            return float(x)
        except ValueError:
            return x
    return x

plans = fetch_plans(limit=5000)

rows = []
for plan in plans:
    pv = safe_get(plan, "planVersion", {})
    year = extract_year(pv)

    if year != 2026:
        continue

    rows.append({
        "plan_id": safe_get(plan, "id"),
        "plan_version_id": safe_get(pv, "id"),
        "plan_code": safe_get(pv, "code"),
        "plan_name": safe_get(pv, "name"),
        "start_date": safe_get(pv, "startDate"),
        "end_date": safe_get(pv, "endDate"),
        "requirements_usd": to_number(extract_requirements(plan))
    })

df = pd.DataFrame(rows).drop_duplicates()

if not df.empty:
    df["requirements_usd_numeric"] = pd.to_numeric(df["requirements_usd"], errors="coerce")
    df = df.sort_values(["requirements_usd_numeric", "plan_name"], ascending=[False, True])
    df = df.drop(columns=["requirements_usd_numeric"])

print(df.to_string(index=False))

output_file = "ocha_hpc_2026_plan_requirements.csv"
df.to_csv(output_file, index=False)
print(f"\nSaved to {output_file}")