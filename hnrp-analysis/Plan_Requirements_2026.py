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
    return None

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

plans = fetch_plans()

rows = []

for plan in plans:
    pv = safe_get(plan, "planVersion", {})
    year = extract_year(pv)

    if year != 2026:
        continue

    code = safe_get(pv, "code")

    rows.append({
        "plan_id": safe_get(plan, "id"),
        "plan_version_id": safe_get(pv, "id"),
        "plan_code": code,
        "plan_name": safe_get(pv, "name"),
        "start_date": safe_get(pv, "startDate"),
        "end_date": safe_get(pv, "endDate"),
        "requirements_usd": to_number(extract_requirements(plan)),
        "plan_group": classify_plan(code)
    })

df = pd.DataFrame(rows).drop_duplicates()

df["requirements_usd"] = pd.to_numeric(df["requirements_usd"], errors="coerce")

df = df.sort_values("requirements_usd", ascending=False)

print(df.to_string(index=False))

df.to_csv("ocha_hpc_2026_plan_requirements.csv", index=False)

print("\nSaved to ocha_hpc_2026_plan_requirements.csv")