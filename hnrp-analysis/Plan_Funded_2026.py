import requests
import pandas as pd
from collections import defaultdict

HPC_URL = "https://api.hpc.tools/v2/public/plan"
FTS_URL = "https://api.hpc.tools/v1/public/fts/flow?year=2026"

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "python-requests"
}


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


def extract_plan_refs_from_flow(flow):
    """
    Pull linked plans out of destinationObjects or sourceObjects.
    We keep both plan id and plan name when available.
    """
    refs = []

    for obj_list_name in ["destinationObjects", "sourceObjects"]:
        obj_list = flow.get(obj_list_name, [])
        if not isinstance(obj_list, list):
            continue

        for obj in obj_list:
            if not isinstance(obj, dict):
                continue

            obj_type = str(obj.get("type", "")).lower()
            obj_id = obj.get("id")
            obj_name = obj.get("name")

            if obj_type in ["plan", "planversion", "coordinatedplan", "appeal", "plan version"]:
                refs.append({
                    "plan_id": obj_id,
                    "plan_name": obj_name,
                    "object_type": obj.get("type")
                })

    return refs


def flow_is_for_2026(flow):
    """
    Double check usage year in the flow objects.
    """
    for obj_list_name in ["destinationObjects", "sourceObjects"]:
        obj_list = flow.get(obj_list_name, [])
        if not isinstance(obj_list, list):
            continue

        for obj in obj_list:
            if not isinstance(obj, dict):
                continue
            if str(obj.get("type", "")).lower() == "usageyear" and str(obj.get("name")) == "2026":
                return True

    return False


print("Fetching HPC plans...")
hpc_payload = fetch_json(HPC_URL, params={"limit": 5000}, timeout=(10, 60))
hpc_plans = hpc_payload["data"]

rows = []
for plan in hpc_plans:
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

df_hpc = pd.DataFrame(rows).drop_duplicates()
df_hpc["requirements_usd"] = pd.to_numeric(df_hpc["requirements_usd"], errors="coerce")

print(f"HPC 2026 plans found: {len(df_hpc)}")

print("Fetching FTS flows...")
fts_payload = fetch_json(FTS_URL, timeout=(10, 180))
fts_flows = fts_payload["data"]["flows"]

print(f"FTS flows found: {len(fts_flows)}")

funded_by_plan_id = defaultdict(float)
funded_by_plan_name = defaultdict(float)

flows_with_plan_refs = 0
sample_plan_refs = []

for flow in fts_flows:
    amount = to_number(flow.get("amountUSD"))
    if amount is None:
        continue

    if not flow_is_for_2026(flow):
        continue

    plan_refs = extract_plan_refs_from_flow(flow)

    if plan_refs:
        flows_with_plan_refs += 1
        if len(sample_plan_refs) < 10:
            sample_plan_refs.append(plan_refs)

    for ref in plan_refs:
        pid = ref.get("plan_id")
        pname = ref.get("plan_name")

        if pid is not None:
            try:
                funded_by_plan_id[int(pid)] += amount
            except Exception:
                pass

        if pname:
            funded_by_plan_name[pname] += amount

print(f"FTS flows with linked plan refs found: {flows_with_plan_refs}")
print(f"Unique plans matched by ID from FTS: {len(funded_by_plan_id)}")
print(f"Unique plans matched by name from FTS: {len(funded_by_plan_name)}")

if sample_plan_refs:
    print("\nSample extracted plan refs from FTS flows:")
    for i, refs in enumerate(sample_plan_refs[:5], 1):
        print(f"{i}: {refs}")
else:
    print("\nNo plan refs found in first pass. You may need to inspect object types in destinationObjects.")


def lookup_funded(row):
    pid = row["plan_id"]
    pname = row["plan_name"]

    if pid in funded_by_plan_id:
        return funded_by_plan_id[pid]
    if pname in funded_by_plan_name:
        return funded_by_plan_name[pname]
    return None


df_hpc["funded_usd"] = df_hpc.apply(lookup_funded, axis=1)
df_hpc["funded_usd"] = pd.to_numeric(df_hpc["funded_usd"], errors="coerce")

df_hpc["coverage_pct"] = (
    df_hpc["funded_usd"] / df_hpc["requirements_usd"] * 100
).round(1)

df_hpc["requirements_usd_m"] = (df_hpc["requirements_usd"] / 1_000_000).round(1)
df_hpc["funded_usd_m"] = (df_hpc["funded_usd"] / 1_000_000).round(1)

df_hpc = df_hpc.sort_values("requirements_usd", ascending=False)

print("\nFirst 20 rows:\n")
print(df_hpc.head(20).to_string(index=False))

output_file = "ocha_hpc_2026_plan_requirements_and_funding.csv"
df_hpc.to_csv(output_file, index=False)
print(f"\nSaved to {output_file}")