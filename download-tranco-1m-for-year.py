#!/usr/bin/env python3
"""
download-tranco-1m-for-year.py
---------------------------------------------------------------
Fetch daily **Tranco Top‑1 M** lists *in parallel* between two dates
(inclusive) and write **one file containing every unique domain** seen
in that span. The resulting file is saved to **./data/** by default.

Default behaviour (no flags)
---------------------------
* `--end`   → **today**  (system date)
* `--start` → **January 1 of that same year**
* `--outfile` → `./data/tranco_unique_domains_<YEAR>.txt` (e.g. `./data/tranco_unique_domains_2025.txt`)

Examples
--------
# Current calendar year‑to‑date (Jan 1 → today), 8 workers
$ python download-tranco-1m-for-year.py

# Full calendar year 2024, 12 workers, custom file name (saved under ./data/)
$ python download-tranco-1m-for-year.py \
      --start 2024-01-01 --end 2024-12-31 \
      --workers 12 --outfile all_unique_2024.txt

Dependencies
------------
- tranco  (pip install tranco)
- tqdm    (pip install tqdm)
"""
import os
import sys
import argparse
from datetime import datetime, timedelta, date
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from typing import Set

from tranco import Tranco   # pip install tranco
from tqdm import tqdm       # pip install tqdm

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="Download Tranco daily Top‑1 M lists, dedupe globally, and write one file of unique domains (saved in ./data/ by default)." )
    parser.add_argument("--start", "-s",
                        help="Start date YYYY-MM-DD (inclusive). Default: Jan 1 of --end's year.")
    parser.add_argument("--end", "-e",
                        help="End date YYYY-MM-DD (inclusive). Default: today.")
    parser.add_argument("--outfile", "-o",
                        help="Output file path (relative paths are placed in ./data/). Default: tranco_unique_domains_<YEAR>.txt if single year, else tranco_unique_domains_<start>_<end>.txt")
    parser.add_argument("--workers", "-w", type=int, default=None,
                        help="Parallel workers (default 8 or env TR_DOWNLOAD_WORKERS)")
    return parser.parse_args()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def daterange(start_date: date, end_date: date):
    """Yield every date from start to end inclusive."""
    cur = start_date
    one_day = timedelta(days=1)
    while cur <= end_date:
        yield cur
        cur += one_day

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = parse_args()

    # Resolve end date (defaults to today)
    if args.end:
        try:
            end_dt = datetime.strptime(args.end, "%Y-%m-%d").date()
        except ValueError as e:
            sys.exit(f"End date parsing error: {e}")
    else:
        end_dt = date.today()

    # Resolve start date (defaults to 1st Jan of end year)
    if args.start:
        try:
            start_dt = datetime.strptime(args.start, "%Y-%m-%d").date()
        except ValueError as e:
            sys.exit(f"Start date parsing error: {e}")
    else:
        start_dt = date(end_dt.year, 1, 1)

    if start_dt > end_dt:
        sys.exit("Error: start date must be earlier than or equal to end date")

    # Determine output file path (relative paths will be rooted under ./data/)
    if args.outfile:
        outfile = args.outfile
    else:
        if start_dt.year == end_dt.year:
            outfile = f"tranco_unique_domains_{start_dt.year}.txt"
        else:
            outfile = f"tranco_unique_domains_{start_dt}_{end_dt}.txt"

    # If the user‑supplied or generated path is not absolute, place it in ./data/
    if not os.path.isabs(outfile):
        outfile = os.path.join("data", outfile)

    # Worker count
    workers = args.workers or int(os.getenv("TR_DOWNLOAD_WORKERS", "8"))
    workers = max(workers, 1)

    # Tranco client with local cache
    tr = Tranco(cache=True, cache_dir=".tranco")

    # Thread‑safe global set
    uniques: Set[str] = set()
    set_lock = Lock()

    def fetch_one(day: date):
        """Return domains for one day and merge into global set."""
        try:
            daily_set = set(tr.list(date=day.isoformat()).top(1_000_000))
            with set_lock:
                uniques.update(daily_set)
            return "ok"
        except Exception as exc:
            tqdm.write(f"[{day}] ERROR: {exc}")
            return "error"

    # Build and execute date tasks
    dates = list(daterange(start_dt, end_dt))

    with ThreadPoolExecutor(max_workers=workers) as pool, \
            tqdm(total=len(dates), unit="day") as bar:
        futures = {pool.submit(fetch_one, d): d for d in dates}
        for fut in as_completed(futures):
            fut.result()  # already handled in fetch_one
            bar.update(1)

    # Ensure output directory exists and write sorted result
    os.makedirs(os.path.dirname(outfile) or ".", exist_ok=True)
    with open(outfile, "w", encoding="utf-8") as fh:
        for domain in sorted(uniques):
            fh.write(f"{domain}\n")

    print(f"\nTotal unique domains: {len(uniques):,}")
    print(f"Saved to: {os.path.abspath(outfile)}")


if __name__ == "__main__":
    main()
