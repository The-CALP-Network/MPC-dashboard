"""
HPC Projects - Merge Script
Combines all hpc_valid_projects_*.csv and hpc_valid_projects_*.json
files in the output folder into single merged files, sorted by project_id.

Run this AFTER the resume scan is complete.
"""

import json
import csv
import os
import glob
from datetime import datetime

# ── Configuration ────────────────────────────────────────────────────────────
OUTPUT_FOLDER = r"C:\Users\rcrew\CALP\CALP - 100 Python working folder\hnrp-analysis\valid id request"
# ─────────────────────────────────────────────────────────────────────────────


def merge_csv_files(folder):
    pattern = os.path.join(folder, "hpc_valid_projects_*.csv")
    files = glob.glob(pattern)
    
    # Exclude any existing merged file
    files = [f for f in files if "merged" not in f]
    
    if not files:
        print("No CSV files found to merge.")
        return

    print(f"Found {len(files)} CSV files to merge:")
    for f in files:
        print(f"  {os.path.basename(f)}")

    all_rows = []
    header = None

    for filepath in files:
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if header is None:
                header = reader.fieldnames
            for row in reader:
                all_rows.append(row)

    # Deduplicate by project_id, keeping first occurrence
    seen = set()
    unique_rows = []
    for row in all_rows:
        pid = row.get("project_id")
        if pid not in seen:
            seen.add(pid)
            unique_rows.append(row)

    # Sort by project_id
    unique_rows.sort(key=lambda x: int(x.get("project_id", 0)))

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(folder, f"hpc_valid_projects_merged_{timestamp}.csv")

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        writer.writerows(unique_rows)

    print(f"\n[OK] CSV merged: {len(unique_rows)} unique projects")
    print(f"     Saved to: {out_path}")
    return out_path


def merge_json_files(folder):
    pattern = os.path.join(folder, "hpc_valid_projects_*.json")
    files = glob.glob(pattern)

    # Exclude any existing merged file
    files = [f for f in files if "merged" not in f]

    if not files:
        print("No JSON files found to merge.")
        return

    print(f"\nFound {len(files)} JSON files to merge:")
    for f in files:
        print(f"  {os.path.basename(f)}")

    all_records = []

    for filepath in files:
        with open(filepath, "r", encoding="utf-8") as f:
            try:
                records = json.load(f)
                all_records.extend(records)
                print(f"  Loaded {len(records)} records from {os.path.basename(filepath)}")
            except json.JSONDecodeError as e:
                print(f"  [WARN] Could not parse {os.path.basename(filepath)}: {e}")
                print(f"         You may need to add a closing ] to this file.")

    # Deduplicate by project_id
    seen = set()
    unique_records = []
    for rec in all_records:
        pid = rec.get("project_id")
        if pid not in seen:
            seen.add(pid)
            unique_records.append(rec)

    # Sort by project_id
    unique_records.sort(key=lambda x: x.get("project_id", 0))

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(folder, f"hpc_valid_projects_merged_{timestamp}.json")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(unique_records, f, indent=2, ensure_ascii=False)

    print(f"\n[OK] JSON merged: {len(unique_records)} unique projects")
    print(f"     Saved to: {out_path}")
    return out_path


def main():
    print("=" * 60)
    print("  HPC Projects - Merge Script")
    print(f"  Folder: {OUTPUT_FOLDER}")
    print("=" * 60)
    print()

    if not os.path.exists(OUTPUT_FOLDER):
        print(f"[ERROR] Folder not found: {OUTPUT_FOLDER}")
        return

    csv_out = merge_csv_files(OUTPUT_FOLDER)
    json_out = merge_json_files(OUTPUT_FOLDER)

    print("\n" + "=" * 60)
    print("  Merge complete!")
    if csv_out:
        print(f"  CSV : {os.path.basename(csv_out)}")
    if json_out:
        print(f"  JSON: {os.path.basename(json_out)}")
    print("=" * 60)


if __name__ == "__main__":
    main()