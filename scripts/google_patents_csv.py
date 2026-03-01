#!/usr/bin/env python3
"""
Google Patents CSV export via XHR endpoint.
Usage: python3 google_patents_csv.py --assignee "Multivac" --out /tmp/gp.csv
No API key required. Rate-limits after ~3 rapid calls; use --delay to control pace.
"""
import argparse
import csv
import io
import time
import urllib.request
import urllib.parse

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Referer": "https://patents.google.com/",
    "Accept-Language": "en-US,en;q=0.5",
}

# Date range slices to work around 20-result-per-query limit
DATE_RANGES = [
    ("", "19991231"),
    ("20000101", "20041231"),
    ("20050101", "20091231"),
    ("20100101", "20121231"),
    ("20130101", "20151231"),
    ("20160101", "20181231"),
    ("20190101", "20211231"),
    ("20220101", "20231231"),
    ("20240101", ""),
]


def build_query(assignee: str, after: str = "", before: str = "") -> str:
    q = f"assignee%3D{urllib.parse.quote(assignee)}"
    if after:
        q += f"%26after%3Dpriority%3A{after}"
    if before:
        q += f"%26before%3Dpriority%3A{before}"
    return q


def fetch_range(assignee: str, after: str, before: str) -> list[dict]:
    q = build_query(assignee, after, before)
    url = f"https://patents.google.com/xhr/query?url={q}&exp=&download=false"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read().decode("utf-8", errors="replace")
    except Exception as exc:
        print(f"    Error fetching {after}-{before}: {exc}")
        return []

    rows = []
    reader = csv.reader(io.StringIO(content))
    header = None
    for row in reader:
        if not row:
            continue
        if row[0].startswith("search URL"):
            continue
        if row[0] == "id":
            header = row
            continue
        if len(row) >= 9 and row[0]:
            rows.append({
                "id": row[0],
                "title": row[1],
                "assignee": row[2],
                "inventor": row[3],
                "priority_date": row[4],
                "filing_date": row[5],
                "publication_date": row[6],
                "grant_date": row[7],
                "link": row[8] if len(row) > 8 else "",
            })
    return rows


def main():
    parser = argparse.ArgumentParser(description="Google Patents CSV export by assignee")
    parser.add_argument("--assignee", required=True, help="Assignee name (e.g. 'Multivac')")
    parser.add_argument("--out", default="/tmp/google_patents.csv", help="Output CSV file")
    parser.add_argument("--delay", type=float, default=2.0, help="Delay between requests (seconds)")
    args = parser.parse_args()

    all_rows = []
    seen_ids = set()

    print(f"Google Patents search: assignee='{args.assignee}'")
    for after, before in DATE_RANGES:
        label = f"{after or 'start'} → {before or 'now'}"
        rows = fetch_range(args.assignee, after, before)
        new = 0
        for r in rows:
            pid = r["id"].upper().replace(" ", "")
            if pid not in seen_ids:
                seen_ids.add(pid)
                all_rows.append(r)
                new += 1
        print(f"  {label}: {len(rows)} results, {new} new")
        time.sleep(args.delay)

    # Write CSV
    if all_rows:
        fieldnames = ["id", "title", "assignee", "inventor",
                      "priority_date", "filing_date", "publication_date", "grant_date", "link"]
        with open(args.out, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_rows)

    print(f"\nTotal unique patents: {len(all_rows)}")
    print(f"Saved to: {args.out}")


if __name__ == "__main__":
    main()
