"""
HPC Tools API Project Scanner - Sequential Version
Scans project codes sequentially from 200000 onwards.
Stops after 500 consecutive failed responses.

Requires: pip install requests
"""

import requests
import time
import json
import csv
import sys
import os
from datetime import datetime

# ── Configuration ────────────────────────────────────────────────────────────
START_ID            = 200000
STOP_AFTER_FAILS    = 500     # Stop after this many consecutive failures
REQUEST_TIMEOUT     = 10      # Seconds before a request times out
DELAY_BETWEEN       = 0.2     # Seconds between requests
DELAY_ON_429        = 30      # Seconds to pause if rate limited
BASE_URL            = "https://api.hpc.tools/v2/public/project/{}"

# Output folder
OUTPUT_FOLDER       = r"C:\Users\rcrew\CALP\CALP - 100 Python working folder\hnrp-analysis\valid id request"

# Output files
TIMESTAMP           = datetime.now().strftime("%Y%m%d_%H%M%S")
CSV_FILE            = f"{OUTPUT_FOLDER}\\hpc_valid_projects_{TIMESTAMP}.csv"
JSON_FILE           = f"{OUTPUT_FOLDER}\\hpc_valid_projects_{TIMESTAMP}.json"
LOG_FILE            = f"{OUTPUT_FOLDER}\\hpc_scan_log_{TIMESTAMP}.txt"
# ─────────────────────────────────────────────────────────────────────────────


def log(msg, log_fh=None):
    print(msg)
    if log_fh:
        log_fh.write(msg + "\n")
        log_fh.flush()


def fetch_project(session, project_id):
    """
    Fetch a single project. Returns (status_code, data_or_none).
    Handles timeouts and connection errors gracefully.
    """
    url = BASE_URL.format(project_id)
    try:
        resp = session.get(url, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 200:
            try:
                data = resp.json()
            except ValueError:
                data = {}
            return 200, data
        return resp.status_code, None
    except requests.exceptions.Timeout:
        return "TIMEOUT", None
    except requests.exceptions.ConnectionError:
        return "CONN_ERROR", None
    except requests.exceptions.RequestException as e:
        return f"ERROR:{e}", None


def main():
    consecutive_fails = 0
    current_id = START_ID
    total_checked = 0
    total_valid = 0
    json_first_record = True

    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    print("=" * 60)
    print("  HPC Tools API Project Scanner (Sequential)")
    print(f"  Starting from ID  : {START_ID}")
    print(f"  Stop condition    : {STOP_AFTER_FAILS} consecutive failures")
    print(f"  Delay between     : {DELAY_BETWEEN}s  |  Timeout: {REQUEST_TIMEOUT}s")
    print("=" * 60)
    print()

    session = requests.Session()
    session.headers.update({"Accept": "application/json"})

    with open(LOG_FILE, "w", encoding="utf-8") as log_fh, \
         open(CSV_FILE, "w", newline="", encoding="utf-8") as csv_fh, \
         open(JSON_FILE, "w", encoding="utf-8") as json_fh:

        csv_writer = csv.writer(csv_fh)
        csv_writer.writerow(["project_id", "url", "name", "status", "raw_keys"])

        # Start JSON array
        json_fh.write("[\n")

        start_time = time.time()
        log(f"Scan started at {datetime.now().isoformat()}", log_fh)
        log("", log_fh)

        while True:
            status, data = fetch_project(session, current_id)

            # ── Rate limit handling ───────────────────────────────────────
            if status == 429:
                msg = f"  [429] Rate limited at ID {current_id}. Waiting {DELAY_ON_429}s..."
                log(msg, log_fh)
                time.sleep(DELAY_ON_429)
                continue  # Retry same ID

            # ── Valid response ────────────────────────────────────────────
            if status == 200 and data:
                consecutive_fails = 0
                total_valid += 1

                name = ""
                if isinstance(data.get("data"), dict):
                    name = data["data"].get("name", "")
                if not name:
                    name = data.get("name", "")

                raw_keys = list(data.keys())
                record = {
                    "project_id": current_id,
                    "url": BASE_URL.format(current_id),
                    "name": name,
                    "status": status,
                    "data": data,
                }

                # Write to CSV immediately
                csv_writer.writerow([
                    current_id,
                    BASE_URL.format(current_id),
                    name,
                    status,
                    json.dumps(raw_keys),
                ])
                csv_fh.flush()

                # Write to JSON immediately
                prefix = "" if json_first_record else ",\n"
                json_first_record = False
                json_fh.write(prefix + json.dumps(record, indent=2, ensure_ascii=False))
                json_fh.flush()

                msg = f"  [OK]  [{current_id}] VALID | Total valid: {total_valid} | Consec. fails reset"
                log(msg, log_fh)

            # ── Failed / not found ────────────────────────────────────────
            else:
                consecutive_fails += 1
                if consecutive_fails % 50 == 0 or consecutive_fails == 1:
                    msg = (f"  [--]  [{current_id}] {str(status):<12} | "
                           f"Consecutive fails: {consecutive_fails}/{STOP_AFTER_FAILS}")
                    log(msg, log_fh)

            total_checked += 1

            # ── Progress every 100 IDs ────────────────────────────────────
            if total_checked % 100 == 0:
                elapsed = time.time() - start_time
                rate = total_checked / elapsed if elapsed > 0 else 0
                log(f"\n  --- Progress: checked={total_checked}, valid={total_valid}, "
                    f"consec_fails={consecutive_fails}, rate={rate:.1f} req/s ---\n", log_fh)

            # ── Stop condition ────────────────────────────────────────────
            if consecutive_fails >= STOP_AFTER_FAILS:
                log(f"\n  [STOP] {STOP_AFTER_FAILS} consecutive failures reached.", log_fh)
                log(f"  Last ID checked: {current_id}", log_fh)
                break

            current_id += 1
            time.sleep(DELAY_BETWEEN)

        # Close JSON array
        json_fh.write("\n]\n")

        # Summary
        elapsed = time.time() - start_time
        summary = (
            f"\n{'=' * 60}\n"
            f"  Scan complete\n"
            f"  IDs checked   : {total_checked}  ({START_ID} -> {current_id})\n"
            f"  Valid projects: {total_valid}\n"
            f"  Time elapsed  : {elapsed:.1f}s  ({elapsed/60:.1f} mins)\n"
            f"  Avg rate      : {total_checked/elapsed:.1f} req/s\n"
            f"  Results saved : {CSV_FILE}\n"
            f"                  {JSON_FILE}\n"
            f"  Log saved     : {LOG_FILE}\n"
            f"{'=' * 60}"
        )
        log(summary, log_fh)

    print(f"\nDone. {total_valid} valid projects saved to {CSV_FILE} and {JSON_FILE}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Partial results already saved to CSV and JSON files.")
        print(f"Note: {JSON_FILE} may need a closing ] added manually if interrupted mid-write.")
        sys.exit(0)