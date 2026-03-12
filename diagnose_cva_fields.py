"""
CVA Field Diagnostic Script
Scans the merged JSON to find all conditionField IDs and names
that relate to CVA across all plans.

Run this BEFORE re-running the extraction script.
"""

import json
import ijson
import os
from collections import defaultdict

OUTPUT_FOLDER = r"C:\Users\rcrew\CALP\CALP - 100 Python working folder\hnrp-analysis\valid id request"
MERGED_JSON   = os.path.join(OUTPUT_FOLDER, "hpc_valid_projects_merged_20260306_181719.json")

# Target project IDs to inspect in detail (CVA projects from known plans)
INSPECT_IDS = {220955, 220583, 209591, 222030, 207336, 200019, 204203, 206531}

# Track all unique field IDs and names seen across all projects
all_cva_fields   = defaultdict(set)   # field_id -> set of field names seen
plan_field_map   = defaultdict(set)   # plan_name -> set of (field_id, field_name)
cva_field_counts = defaultdict(int)   # field_id -> count of projects where value="true"
field_name_index = {}                 # field_id -> most common name

print("=" * 65)
print("  CVA Field Diagnostic")
print(f"  Scanning: {os.path.basename(MERGED_JSON)}")
print("=" * 65)
print()

processed = 0
inspected = {}

with open(MERGED_JSON, "r", encoding="utf-8") as f:
    for project in ijson.items(f, "item"):
        project_id = project.get("project_id")
        data = project.get("data", {})
        if "data" in data:
            data = data["data"]

        versions = data.get("projectVersions", [])
        if not versions:
            processed += 1
            continue

        pv = versions[-1]
        plan_name = ""

        # Get plan name
        plans = pv.get("plans", [])
        if plans:
            plan_name = plans[0].get("planVersion", {}).get("name", "")

        # Build field name lookup from conditionFields
        field_names = {}
        for plan in plans:
            for cf in plan.get("conditionFields", []):
                fid = cf.get("id")
                fname = (cf.get("name") or "").strip()
                if fid and fname:
                    field_names[fid] = fname
                    field_name_index[fid] = fname

        # Scan projectVersionFields for CVA-related fields
        for pvp in pv.get("projectVersionPlans", []):
            for field in pvp.get("projectVersionFields", []):
                cf_id = field.get("conditionFieldId")
                val   = str(field.get("value") or "").strip().lower()
                fname = field_names.get(cf_id, "")

                # Index any field whose name mentions CVA, cash, or voucher
                if fname and any(kw in fname.lower() for kw in ["cva", "cash", "voucher", "transfer"]):
                    all_cva_fields[cf_id].add(fname)
                    plan_field_map[plan_name].add((cf_id, fname[:60]))

                    # Count how many projects have this field set to true
                    if val == "true":
                        cva_field_counts[cf_id] += 1

        # Detailed inspection of target projects
        if project_id in INSPECT_IDS:
            detail = {
                "plan": plan_name,
                "fields": []
            }
            for pvp in pv.get("projectVersionPlans", []):
                for field in pvp.get("projectVersionFields", []):
                    cf_id = field.get("conditionFieldId")
                    val   = field.get("value")
                    fname = field_names.get(cf_id, f"[unknown field {cf_id}]")
                    detail["fields"].append({
                        "id": cf_id,
                        "name": fname[:70],
                        "value": str(val)[:50]
                    })
            inspected[project_id] = detail

        processed += 1
        if processed % 2000 == 0:
            print(f"  Scanned {processed:,} projects...")

print(f"  Done. Scanned {processed:,} projects total.")
print()

# ── Results ──────────────────────────────────────────────────────────────────

print("=" * 65)
print("  ALL CVA-RELATED CONDITION FIELDS FOUND")
print("=" * 65)
print(f"{'Field ID':<12} {'True count':>10}  Name")
print("-" * 65)
for fid, names in sorted(all_cva_fields.items(), key=lambda x: -cva_field_counts[x[0]]):
    name = list(names)[0]
    count = cva_field_counts[fid]
    print(f"  {fid:<10} {count:>10}  {name[:55]}")

print()
print("=" * 65)
print("  CVA FIELDS BY PLAN")
print("=" * 65)
for plan, fields in sorted(plan_field_map.items()):
    cva_fields = [(fid, fname) for fid, fname in fields
                  if any(kw in fname.lower() for kw in ["cva", "cash", "voucher"])]
    if cva_fields:
        print(f"\n  {plan[:65]}")
        for fid, fname in sorted(cva_fields):
            count = cva_field_counts.get(fid, 0)
            print(f"    [{fid}] {fname[:55]}  (true={count})")

print()
print("=" * 65)
print("  DETAILED INSPECTION OF TARGET PROJECTS")
print("=" * 65)
for pid, detail in sorted(inspected.items()):
    print(f"\n  Project {pid} | {detail['plan'][:60]}")
    for f in detail["fields"]:
        print(f"    [{f['id']}] {f['name'][:55]} = {f['value']}")

print()
print("Copy the field IDs above and share with Claude to fix the extraction script.")