"""
HPC Projects - Extraction Script
Reads the merged JSON file and extracts all fields needed for the dashboard.
Outputs a clean flat CSV ready for the dashboard builder.

Requires: pip install requests (for Claude API summaries)
"""

import json
import csv
import os
import sys
from datetime import datetime, date

# ── Configuration ────────────────────────────────────────────────────────────
OUTPUT_FOLDER   = r"C:\Users\rcrew\CALP\CALP - 100 Python working folder\hnrp-analysis\valid id request"

# Set this to your merged JSON filename
MERGED_JSON     = os.path.join(OUTPUT_FOLDER, "hpc_valid_projects_merged_20260306_181719.json")

# Output CSV
TIMESTAMP       = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_CSV      = os.path.join(OUTPUT_FOLDER, f"hpc_extracted_{TIMESTAMP}.csv")
OUTPUT_JSON     = os.path.join(OUTPUT_FOLDER, f"hpc_extracted_{TIMESTAMP}.json")

# CVA keywords for objective text fallback
CVA_KEYWORDS = [
    "cash transfer", "cash assistance", "voucher", "cva", "mpca",
    "multi-purpose cash", "multipurpose cash", "unconditional cash",
    "cash grant", "cash distribution", "in-kind transfer"
]

# Today's date for 2026 vs 2025 comparison cutoff
TODAY = date.today()
COMPARISON_CUTOFF = TODAY.strftime("%m-%d")  # e.g. "03-06"
# ─────────────────────────────────────────────────────────────────────────────


def safe_get(d, *keys, default=""):
    """Safely navigate nested dict/list."""
    val = d
    for key in keys:
        if isinstance(val, dict):
            val = val.get(key, default)
        elif isinstance(val, list) and isinstance(key, int):
            val = val[key] if len(val) > key else default
        else:
            return default
        if val is None:
            return default
    return val if val is not None else default


def get_latest_version(project):
    """Get the latest project version from a project record."""
    data = project.get("data", {})
    # Handle double-nested structure: record['data']['data']
    if "data" in data:
        data = data["data"]
    versions = data.get("projectVersions", [])
    if not versions:
        return None
    # Return last version (most recent)
    return versions[-1]


def is_cva_checkbox_field(fname):
    """
    Return True if this field name is a CVA yes/no checkbox.
    Covers English, French, Spanish variants found across all plans.
    """
    f = fname.lower()
    # English patterns
    if "does this project involve cva" in f: return True
    if "check this box if this project is cva" in f: return True
    if "is the project using cash or voucher" in f: return True
    if "cash and voucher assistance (cva)?" in f: return True
    if "project include" in f and "transfer" in f: return True
    if "sectoral cash" in f: return True
    if "cash-based" in f: return True
    # French patterns
    if "monétaire-coupons" in f: return True
    if "transfert monétaire inclus" in f: return True
    if "transfert monetaire" in f: return True
    if "le projet inclut-il des transferts" in f: return True
    if "projet intègre t-il une composante cash" in f: return True
    if "le projet utilise-t-il le mode" in f: return True
    # Spanish patterns
    if "transferencias monetarias o cupones" in f: return True
    if "el proyecto incluye transferencias" in f: return True
    if "transferencias monetarias" in f: return True
    return False


def is_cash_pct_field(fname):
    """Return True if this field captures % cash transfer."""
    f = fname.lower()
    patterns = [
        ("cash transfer", "%"), ("cash transfer", "percent"),
        ("espèces", "%"), ("espèces", "estimé"),
        ("especes", "%"), ("cash", "% estimé"),
        ("monetario", "porcentaje"), ("monetarias", "porcentaje"),
        ("cash programming", "percentage"), ("cash", "estimated %"),
        ("cash", "% of financial"), ("cash", "% of requirement"),
    ]
    suffix_ids = ["1.1.1", "3.1.1", "4.1.1", "3.1.a", "4.1", "6.1.a",
                  "3.2.a", "1.1.a", "9.1.1", "5.2.1", "3.2.1"]
    for sid in suffix_ids:
        if f.startswith(sid) and any(kw in f for kw in ["cash", "espèces", "monetar", "transfer"]):
            return True
    for p1, p2 in patterns:
        if p1 in f and p2 in f:
            return True
    return False


def is_voucher_pct_field(fname):
    """Return True if this field captures % voucher assistance."""
    f = fname.lower()
    patterns = [
        ("voucher", "%"), ("voucher", "percent"),
        ("coupon", "%"), ("coupon", "estimé"),
        ("cupón", "porcentaje"), ("cupones", "porcentaje"),
        ("voucher", "estimated %"), ("voucher", "% of"),
    ]
    suffix_ids = ["1.1.2", "3.1.2", "4.1.2", "3.1.b", "4.2", "6.1.b",
                  "3.2.b", "1.1.b", "9.1.2"]
    for sid in suffix_ids:
        if f.startswith(sid) and any(kw in f for kw in ["voucher", "coupon", "cupón"]):
            return True
    for p1, p2 in patterns:
        if p1 in f and p2 in f:
            return True
    return False


def extract_cva_fields(pv):
    """
    Extract CVA checkbox, % cash, % voucher from projectVersionPlans[].projectVersionFields[].
    Field IDs vary by plan/year/language — we match by field name patterns instead.
    Covers English, French, and Spanish HRP forms.
    """
    result = {
        "cva_flag": False,
        "cva_flag_source": "",
        "cva_pct_cash": None,
        "cva_pct_voucher": None,
        "cva_value": None,
    }

    requested_funds = float(safe_get(pv, "currentRequestedFunds") or 0)

    # Build lookup: conditionFieldId -> field name
    field_name_lookup = {}
    for plan in pv.get("plans", []):
        for cf in plan.get("conditionFields", []):
            fid = cf.get("id")
            fname = (cf.get("name") or "").strip()
            if fid and fname:
                field_name_lookup[fid] = fname

    # Read filled values from projectVersionPlans[].projectVersionFields[]
    for pvp in pv.get("projectVersionPlans", []):
        for field in pvp.get("projectVersionFields", []):
            cf_id = field.get("conditionFieldId")
            val   = field.get("value")
            fname = field_name_lookup.get(cf_id, "")

            if not fname:
                continue

            val_str = str(val).strip().lower() if val is not None else ""

            # CVA checkbox
            if is_cva_checkbox_field(fname):
                if val_str == "true":
                    result["cva_flag"] = True
                    result["cva_flag_source"] = f"conditionField:{cf_id}:{fname[:40]}"

            # % cash
            elif is_cash_pct_field(fname):
                if val_str not in ("", "none", "null", "0"):
                    try:
                        pct = float(val)
                        if 0 < pct <= 100:
                            result["cva_pct_cash"] = pct
                    except (TypeError, ValueError):
                        pass

            # % voucher
            elif is_voucher_pct_field(fname):
                if val_str not in ("", "none", "null", "0"):
                    try:
                        pct = float(val)
                        if 0 < pct <= 100:
                            result["cva_pct_voucher"] = pct
                    except (TypeError, ValueError):
                        pass

    # Calculate CVA value
    if result["cva_flag"] and requested_funds > 0:
        if result["cva_pct_cash"] is not None or result["cva_pct_voucher"] is not None:
            cash_pct    = (result["cva_pct_cash"]    or 0) / 100
            voucher_pct = (result["cva_pct_voucher"] or 0) / 100
            result["cva_value"] = requested_funds * (cash_pct + voucher_pct)

    return result


def extract_people_targeted(pv):
    """Try to extract number of people targeted from attachments/indicators."""
    people = None

    for att in pv.get("attachments", []):
        att_value = att.get("value") or {}
        if isinstance(att_value, str):
            try:
                att_value = json.loads(att_value)
            except Exception:
                att_value = {}

        # Look for indicators with "people" or "beneficiar" in name
        metrics = att_value.get("metrics", {})
        if isinstance(metrics, dict):
            for metric_key, metric_val in metrics.items():
                if isinstance(metric_val, dict):
                    name = str(metric_val.get("name", "")).lower()
                    if any(k in name for k in ["people", "beneficiar", "targeted", "reached"]):
                        try:
                            people = float(metric_val.get("value", 0) or 0)
                            if people > 0:
                                return people
                        except (TypeError, ValueError):
                            pass

    # Check budget segments for target population
    for seg in pv.get("budgetSegments", []):
        breakdown = seg.get("breakdown", [])
        for item in breakdown:
            name = str(item.get("name", "")).lower()
            if "people" in name or "beneficiar" in name:
                try:
                    people = float(item.get("value", 0) or 0)
                    if people > 0:
                        return people
                except (TypeError, ValueError):
                    pass

    return people


def project_duration_days(start_str, end_str):
    """Calculate project duration in days."""
    try:
        start = datetime.strptime(start_str[:10], "%Y-%m-%d").date()
        end = datetime.strptime(end_str[:10], "%Y-%m-%d").date()
        return (end - start).days
    except Exception:
        return None


def spans_multiple_years(start_str, end_str):
    """Check if project spans more than one calendar year."""
    try:
        start = datetime.strptime(start_str[:10], "%Y-%m-%d")
        end = datetime.strptime(end_str[:10], "%Y-%m-%d")
        return end.year > start.year
    except Exception:
        return False


def extract_project(project):
    """Extract all fields from a single project record."""
    project_id = project.get("project_id", "")
    data = project.get("data", {})

    if not data:
        return None

    pv = get_latest_version(project)
    if not pv:
        return None

    # ── Core fields ───────────────────────────────────────────────────────────
    start_date  = safe_get(pv, "startDate")
    end_date    = safe_get(pv, "endDate")
    start_year  = start_date[:4] if start_date else ""

    # ── Plan info (first plan = primary) ─────────────────────────────────────
    plans = pv.get("plans", [])
    plan_name = ""
    plan_code = ""
    plan_year = ""
    plan_id   = ""

    if plans:
        plan_version = plans[0].get("planVersion", {})
        plan_name = safe_get(plan_version, "name")
        plan_code = safe_get(plan_version, "code")
        plan_id   = safe_get(plans[0], "id")
        # Extract year from plan code e.g. HSDN24 -> 2024
        if plan_code:
            # Last 2 digits of code = year suffix
            for i, ch in enumerate(plan_code):
                if ch.isdigit() and i > 0:
                    year_suffix = plan_code[i:i+2]
                    if len(year_suffix) == 2:
                        try:
                            yr = int(year_suffix)
                            plan_year = str(2000 + yr) if yr < 50 else str(1900 + yr)
                        except ValueError:
                            pass
                    break

    # ── Organisation (first = primary) ───────────────────────────────────────
    orgs = pv.get("organizations", [])
    org_name  = safe_get(orgs, 0, "name") if orgs else ""
    org_abbr  = safe_get(orgs, 0, "abbreviation") if orgs else ""
    org_count = len(orgs)

    # ── Global cluster (first = primary) ─────────────────────────────────────
    clusters = pv.get("globalClusters", [])
    cluster_name = safe_get(clusters, 0, "name") if clusters else ""
    cluster_code = safe_get(clusters, 0, "code") if clusters else ""
    cluster_count = len(clusters)
    all_clusters = "|".join([c.get("name", "") for c in clusters])

    # ── Governing entity ─────────────────────────────────────────────────────
    gov_entities = pv.get("governingEntities", [])
    gov_entity_name = ""
    gov_entity_code = ""
    if gov_entities:
        gev = gov_entities[0].get("governingEntityVersion", {})
        gov_entity_name = safe_get(gev, "name")
        gov_entity_code = safe_get(gev, "custom")

    # ── Financial ─────────────────────────────────────────────────────────────
    requested_funds = safe_get(pv, "currentRequestedFunds")
    try:
        requested_funds = float(requested_funds) if requested_funds else 0.0
    except (TypeError, ValueError):
        requested_funds = 0.0

    # ── CVA ───────────────────────────────────────────────────────────────────
    cva = extract_cva_fields(pv)

    # ── People targeted ───────────────────────────────────────────────────────
    people_targeted = extract_people_targeted(pv)

    # ── Duration ─────────────────────────────────────────────────────────────
    duration_days = project_duration_days(start_date, end_date)
    multi_year = spans_multiple_years(start_date, end_date)

    # ── Location ─────────────────────────────────────────────────────────────
    locations = pv.get("locations", [])
    location_names = "|".join([
        loc.get("name", "") for loc in locations
        if isinstance(loc, dict) and loc.get("adminLevel", 99) <= 1
    ])

    # ── Tags ─────────────────────────────────────────────────────────────────
    tags = "|".join(pv.get("tags", []) or [])

    return {
        # IDs
        "project_id":           project_id,
        "project_version_id":   safe_get(pv, "id"),
        "plan_id":              plan_id,

        # Core
        "code":                 safe_get(pv, "code"),
        "name":                 safe_get(pv, "name"),
        "status":               safe_get(pv, "implementationStatus"),
        "objective":            (safe_get(pv, "objective") or "")[:500],  # truncate for CSV

        # Dates
        "start_date":           start_date,
        "end_date":             end_date,
        "start_year":           start_year,
        "duration_days":        duration_days,
        "multi_year":           multi_year,

        # Plan
        "plan_name":            plan_name,
        "plan_code":            plan_code,
        "plan_year":            plan_year,

        # Organisation
        "org_name":             org_name,
        "org_abbreviation":     org_abbr,
        "org_count":            org_count,

        # Cluster
        "primary_cluster_name": cluster_name,
        "primary_cluster_code": cluster_code,
        "cluster_count":        cluster_count,
        "all_clusters":         all_clusters,

        # Governing entity
        "governing_entity_name": gov_entity_name,
        "governing_entity_code": gov_entity_code,

        # Financial
        "requested_funds_usd":  requested_funds,

        # CVA
        "cva_flag":             cva["cva_flag"],
        "cva_flag_source":      cva["cva_flag_source"],
        "cva_pct_cash":         cva["cva_pct_cash"],
        "cva_pct_voucher":      cva["cva_pct_voucher"],
        "cva_value_usd":        cva["cva_value"],

        # People
        "people_targeted":      people_targeted,

        # Location
        "locations":            location_names,

        # Tags
        "tags":                 tags,
    }


def main():
    print("=" * 60)
    print("  HPC Projects - Extraction Script")
    print(f"  Input : {os.path.basename(MERGED_JSON)}")
    print(f"  Output: {os.path.basename(OUTPUT_CSV)}")
    print("=" * 60)
    print()

    if not os.path.exists(MERGED_JSON):
        print(f"[ERROR] Merged JSON not found: {MERGED_JSON}")
        print("Please update MERGED_JSON at the top of the script to match your filename.")
        sys.exit(1)

    # Stream JSON record by record to avoid loading 4GB into memory
    print("Streaming JSON file record by record (memory efficient)...")
    print("(This avoids loading the full 4GB file at once)")
    print()

    extracted = []
    skipped = 0
    errors = 0
    i = 0

    # We stream the JSON array manually using ijson if available, else fallback
    try:
        import ijson
        use_ijson = True
    except ImportError:
        use_ijson = False

    if use_ijson:
        print("Using ijson streaming parser...")
        with open(MERGED_JSON, "r", encoding="utf-8") as f:
            for project in ijson.items(f, "item"):
                try:
                    row = extract_project(project)
                    if row:
                        extracted.append(row)
                    else:
                        skipped += 1
                except Exception as e:
                    errors += 1
                    if errors <= 5:
                        print(f"  [WARN] Error on project {project.get('project_id', '?')}: {e}")
                i += 1
                if i % 1000 == 0:
                    print(f"  Processed {i:,} projects | Found {len(extracted):,} valid...")
    else:
        # Fallback: manual line-by-line parsing
        # Works because each record in the merged JSON is separated by },\n{
                print("ijson not found - using line-by-line parser...")
        print("(Run 'pip install ijson' for faster streaming)")
        print()

        buffer = ""
        depth = 0
        in_record = False
        max_buffer_size = 10_000_000  # 10MB safety limit per record
        line_count = 0

        with open(MERGED_JSON, "r", encoding="utf-8") as f:
            for line in f:
                line_count += 1
                stripped = line.strip()

                # Skip array brackets at file level
                if stripped in ("[", "]"):
                    continue

                # Track brace depth to find complete records
                for ch in stripped:
                    if ch == "{":
                        depth += 1
                        in_record = True
                    elif ch == "}":
                        depth -= 1

                if in_record:
                    buffer += line
                    
                    # Safety check: prevent infinite buffer growth
                    if len(buffer) > max_buffer_size:
                        print(f"  [WARN] Line {line_count}: Buffer exceeded {max_buffer_size:,} bytes - skipping malformed record")
                        buffer = ""
                        depth = 0
                        in_record = False
                        errors += 1
                        continue

                # When depth returns to 0 we have a complete record
                if in_record and depth == 0:
                    # Clean up the buffer (remove trailing comma)
                    clean = buffer.strip().rstrip(",")
                    if clean:
                        try:
                            project = json.loads(clean)
                            row = extract_project(project)
                            if row:
                                extracted.append(row)
                            else:
                                skipped += 1
                        except json.JSONDecodeError as e:
                            errors += 1
                            if errors <= 5:
                                print(f"  [WARN] JSON parse error at line {line_count}: {e}")
                        except Exception as e:
                            errors += 1
                            if errors <= 5:
                                print(f"  [WARN] Extraction error at line {line_count}: {e}")
                    elif buffer.strip():
                        # Buffer has content but failed to parse
                        errors += 1
                        if errors <= 5:
                            print(f"  [WARN] Line {line_count}: Could not parse record (buffer size: {len(buffer):,} bytes)")
                    
                    # Reset for next record
                    buffer = ""
                    in_record = False
                    i += 1
                    if i % 1000 == 0:
                        print(f"  Processed {i:,} projects | Found {len(extracted):,} valid... (line {line_count:,})")
                
                # Safety check: depth should never go negative
                if depth < 0:
                    print(f"  [WARN] Line {line_count}: Depth went negative - resetting parser state")
                    buffer = ""
                    depth = 0
                    in_record = False
                    errors += 1

    print()
    print(f"Extracted : {len(extracted):,} projects")
    print(f"Skipped   : {skipped:,} (no data)")
    print(f"Errors    : {errors:,}")
    print()

    if not extracted:
        print("[ERROR] No projects extracted. Check your JSON file.")
        sys.exit(1)

    # Write CSV
    fieldnames = list(extracted[0].keys())
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(extracted)
    print(f"[OK] CSV saved: {OUTPUT_CSV}")

    # Write JSON summary (lighter version without objective text)
    summary_records = []
    for row in extracted:
        r = dict(row)
        r.pop("objective", None)
        summary_records.append(r)

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(summary_records, f, indent=2, ensure_ascii=False, default=str)
    print(f"[OK] JSON saved: {OUTPUT_JSON}")

    # Print quick stats
    print()
    print("=" * 60)
    print("  QUICK STATS")
    print("=" * 60)

    total_funds = sum(r["requested_funds_usd"] for r in extracted)
    cva_projects = [r for r in extracted if r["cva_flag"]]
    cva_value = sum(r["cva_value_usd"] for r in extracted if r["cva_value_usd"])
    multi_year = sum(1 for r in extracted if r["multi_year"])

    print(f"  Total projects        : {len(extracted):,}")
    print(f"  Total requirements    : ${total_funds:,.0f}")
    print(f"  CVA projects          : {len(cva_projects):,} ({len(cva_projects)/len(extracted)*100:.1f}%)")
    print(f"  Total CVA value       : ${cva_value:,.0f}")
    print(f"  Multi-year projects   : {multi_year:,}")
    print()

    # By year
    from collections import Counter
    years = Counter(r["start_year"] for r in extracted if r["start_year"])
    print("  Projects by start year:")
    for yr, count in sorted(years.items()):
        yr_funds = sum(r["requested_funds_usd"] for r in extracted if r["start_year"] == yr)
        print(f"    {yr}: {count:,} projects | ${yr_funds:,.0f}")
    print()

    # By plan
    plans = Counter(r["plan_name"] for r in extracted if r["plan_name"])
    print(f"  Top 10 plans by project count:")
    for plan, count in plans.most_common(10):
        print(f"    {plan[:60]}: {count:,}")

    print()
    print("Done! Use the extracted CSV/JSON to build the dashboard.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(0)