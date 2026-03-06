"""
HDX HRP Project ID Extractor
==============================
This script:
  1. Queries the HDX CKAN API for all 'hrp-projects-*' datasets
  2. Finds the latest CSV/Excel resource in each dataset
  3. Downloads it, reads the VersionCode column
  4. Extracts the numeric project ID and year from each code
     e.g.  HSDN24-HEA;WSH;NUT;PRO;SHL-208805-1  →  208805, 2024
           HCOL24-CSS-205657-1                   →  205657, 2024
           HUKR25-FSC-312441-1                   →  312441, 2025
  5. Saves a three-column CSV: country_code, project_id, year

Requirements:
    pip install requests pandas openpyxl

Usage:
    python extract_hrp_project_ids.py

    # Optional: narrow to specific countries
    python extract_hrp_project_ids.py --countries COL SDN UKR
"""

import re
import sys
import argparse
import io
import logging
import time

import requests
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

HDX_API   = "https://data.humdata.org/api/3/action"
HDX_FILES = "https://data.humdata.org"
OUTPUT    = "hrp_project_ids.csv"

# Regex to pull the numeric ID out of a VersionCode string.
# Matches the last numeric segment before the final "-<digit>" suffix.
# e.g.  HSDN24-HEA;WSH-208805-1  →  208805
#        HCOL24-CSS-205657-1      →  205657
VERSION_CODE_RE = re.compile(r"-(\d{5,7})-\d+$")

# Regex to pull the 2-digit year from the start of a VersionCode string.
# e.g.  HCOL24-CSS-205657-1  →  24  →  2024
#        HSDN25-HEA-208805-1  →  25  →  2025
YEAR_RE = re.compile(r"^H[A-Z]{2,3}(\d{2})-")


# ---------------------------------------------------------------------------
# HDX API helpers
# ---------------------------------------------------------------------------

def get_all_hrp_datasets(session: requests.Session) -> list[dict]:
    """Return every dataset whose name starts with 'hrp-projects-'."""
    all_pkgs: list[dict] = []
    rows = 100
    start = 0
    while True:
        resp = session.get(
            f"{HDX_API}/package_search",
            params={"q": "name:hrp-projects-*", "rows": rows, "start": start},
            timeout=30,
        )
        resp.raise_for_status()
        result = resp.json()["result"]
        batch  = result["results"]
        all_pkgs.extend(batch)
        log.info("  fetched %d / %d datasets …", len(all_pkgs), result["count"])
        if len(all_pkgs) >= result["count"]:
            break
        start += rows
        time.sleep(0.3)
    return all_pkgs


def country_code_from_name(dataset_name: str) -> str:
    """
    Strip 'hrp-projects-' prefix and return the country code in uppercase.
    e.g. 'hrp-projects-col' → 'COL'
    """
    return dataset_name.removeprefix("hrp-projects-").upper()


def pick_best_resource(resources: list[dict]) -> dict | None:
    """
    Choose the CSV or Excel resource to download.
    Prefers CSV; falls back to xlsx/xls.
    Within each format, picks the most recently created/modified one.
    """
    def _score(r: dict) -> tuple:
        fmt = (r.get("format") or "").lower()
        ext = (r.get("name") or "").lower()
        is_csv  = fmt == "csv"  or ext.endswith(".csv")
        is_xlsx = fmt in ("xlsx","xls") or ext.endswith((".xlsx",".xls"))
        priority = 2 if is_csv else (1 if is_xlsx else 0)
        ts = r.get("last_modified") or r.get("created") or ""
        return (priority, ts)

    candidates = [r for r in resources if _score(r)[0] > 0]
    if not candidates:
        return None
    return max(candidates, key=_score)


# ---------------------------------------------------------------------------
# Download & parse
# ---------------------------------------------------------------------------

def download_resource(session: requests.Session, resource: dict) -> bytes | None:
    """Download a resource and return raw bytes, or None on failure."""
    url = resource.get("download_url") or resource.get("url")
    if not url:
        return None
    # HDX sometimes gives relative URLs
    if url.startswith("/"):
        url = HDX_FILES + url
    try:
        resp = session.get(url, timeout=60)
        resp.raise_for_status()
        return resp.content
    except Exception as exc:
        log.warning("    ⚠  download failed: %s", exc)
        return None


def read_dataframe(raw: bytes, resource: dict) -> pd.DataFrame | None:
    """Parse raw bytes into a DataFrame based on the resource format."""
    fmt  = (resource.get("format") or "").lower()
    name = (resource.get("name")   or "").lower()
    try:
        if fmt == "csv" or name.endswith(".csv"):
            return pd.read_csv(io.BytesIO(raw), dtype=str, low_memory=False)
        else:
            return pd.read_excel(io.BytesIO(raw), dtype=str)
    except Exception as exc:
        log.warning("    ⚠  parse failed: %s", exc)
        return None


def extract_project_ids(df: pd.DataFrame, country_code: str) -> list[dict]:
    """
    Find the VersionCode column (case-insensitive) and extract numeric IDs + year.
    Returns a list of {"country_code": ..., "project_id": ..., "year": ...} dicts.
    """
    # Locate column
    col = next(
        (c for c in df.columns if c.strip().lower() == "versioncode"),
        None,
    )
    if col is None:
        log.warning("    ⚠  no 'VersionCode' column in %s – columns: %s",
                    country_code, list(df.columns[:10]))
        return []

    rows = []
    for raw_val in df[col].dropna().unique():
        val = str(raw_val).strip()
        id_match   = VERSION_CODE_RE.search(val)
        year_match = YEAR_RE.search(val)
        if id_match:
            year = ("20" + year_match.group(1)) if year_match else None
            rows.append({
                "country_code": country_code,
                "project_id":   id_match.group(1),
                "year":         year,
            })
        else:
            log.debug("    skipped unmatched code: %r", val)

    return rows


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(filter_codes: list[str] | None = None) -> None:
    session = requests.Session()
    session.headers.update({"User-Agent": "hrp-extractor/1.0"})

    # ── Step 1: discover datasets ────────────────────────────────────────
    log.info("Querying HDX for hrp-projects datasets …")
    try:
        datasets = get_all_hrp_datasets(session)
    except Exception as exc:
        log.error("Failed to query HDX API: %s", exc)
        sys.exit(1)

    hrp_datasets = [d for d in datasets if d["name"].startswith("hrp-projects-")]
    log.info("Found %d hrp-projects datasets.", len(hrp_datasets))

    if filter_codes:
        filter_codes_upper = {c.upper() for c in filter_codes}
        hrp_datasets = [
            d for d in hrp_datasets
            if country_code_from_name(d["name"]) in filter_codes_upper
        ]
        log.info("Filtered to %d datasets: %s", len(hrp_datasets),
                 [d["name"] for d in hrp_datasets])

    # ── Step 2–4: download, parse, extract ───────────────────────────────
    all_rows: list[dict] = []
    skipped: list[str]   = []

    for i, pkg in enumerate(hrp_datasets, 1):
        cc   = country_code_from_name(pkg["name"])
        name = pkg["name"]
        log.info("[%d/%d] %s (%s)", i, len(hrp_datasets), name, cc)

        resources = pkg.get("resources", [])
        resource  = pick_best_resource(resources)
        if not resource:
            log.warning("  ⚠  no usable CSV/Excel resource found – skipping")
            skipped.append(cc)
            continue

        log.info("  → downloading: %s", resource.get("name") or resource.get("url"))
        raw = download_resource(session, resource)
        if raw is None:
            skipped.append(cc)
            continue

        df = read_dataframe(raw, resource)
        if df is None:
            skipped.append(cc)
            continue

        rows = extract_project_ids(df, cc)
        log.info("  ✓  extracted %d unique project IDs", len(rows))
        all_rows.extend(rows)
        time.sleep(0.5)   # be polite

    # ── Step 5: save ─────────────────────────────────────────────────────
    if not all_rows:
        log.warning("No project IDs extracted – check warnings above.")
        return

    out_df = (
        pd.DataFrame(all_rows)
          .drop_duplicates()
          .sort_values(["country_code", "year", "project_id"])
          .reset_index(drop=True)
    )

    out_df.to_csv(OUTPUT, index=False)
    log.info("")
    log.info("═══════════════════════════════════════════")
    log.info("  Saved %d rows to %s", len(out_df), OUTPUT)
    log.info("  Countries: %d", out_df["country_code"].nunique())
    log.info("═══════════════════════════════════════════")

    if skipped:
        log.warning("Skipped %d countries (no data or errors): %s", len(skipped), skipped)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--countries", nargs="*", metavar="CODE",
        help="Optional 3-letter country codes to limit processing (e.g. COL SDN UKR)"
    )
    args = parser.parse_args()
    main(filter_codes=args.countries)