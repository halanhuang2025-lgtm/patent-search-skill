#!/usr/bin/env python3
"""
FreePatentsOnline bulk assignee search.
Usage: python3 fpo_search.py --assignee "MULTIVAC SEPP HAGGENMUELLER" --pages 10 --out /tmp/results.json
"""
import argparse
import json
import re
import time
import urllib.request
import urllib.parse

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

def fetch_page(assignee: str, page: int, num: int = 50) -> list[dict]:
    """Fetch one page of FPO results."""
    params = {
        "p": str(page),
        "num": str(num),
        "srchtype": "assignee",
        "srchoption": "",
        "query_txt": assignee,
        "daterange": "application",
        "startdate": "",
        "enddate": "",
        "dbase": "US",
        "search": "Search",
    }
    url = "https://www.freepatentsonline.com/result.html?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        html = resp.read().decode("utf-8", errors="replace")

    # HTML structure:
    # <td>8825569</td>
    # <td><a href="/8825569.html">Title text</a>
    # OR: <td>US20120323830</td> <td><a href="...">TITLE</a>
    entries = []
    pattern = re.compile(
        r'<td[^>]*>\s*((?:US|EP|WO|DE|GB|FR|JP|CN|D)\d[\w-]*|\d{6,10})\s*</td>'
        r'.*?<a\s+href="[^"]+">([^<]{5,150})</a>',
        re.DOTALL
    )
    seq = 0
    for m in pattern.finditer(html):
        patent_id = m.group(1).strip()
        title = re.sub(r'\s+', ' ', m.group(2)).strip()
        # Skip very short or noise titles
        if len(title) < 8:
            continue
        seq += 1
        entries.append({
            "seq": seq,
            "id": patent_id,
            "title": title,
        })

    return entries


def main():
    parser = argparse.ArgumentParser(description="Search FreePatentsOnline by assignee")
    parser.add_argument("--assignee", required=True, help="Assignee name to search")
    parser.add_argument("--pages", type=int, default=10, help="Max pages to fetch (50 results/page)")
    parser.add_argument("--out", default="/tmp/fpo_patents.json", help="Output JSON file")
    parser.add_argument("--delay", type=float, default=1.2, help="Delay between requests (seconds)")
    args = parser.parse_args()

    all_patents = []
    seen_ids = set()

    print(f"Searching FreePatentsOnline: assignee='{args.assignee}'")
    for page in range(1, args.pages + 1):
        try:
            entries = fetch_page(args.assignee, page)
            if not entries:
                print(f"  Page {page}: no results, stopping.")
                break

            new = 0
            for e in entries:
                if e["id"] not in seen_ids:
                    seen_ids.add(e["id"])
                    all_patents.append(e)
                    new += 1

            max_seq = max(e["seq"] for e in entries) if entries else 0
            print(f"  Page {page}: {len(entries)} entries, {new} new (total seq up to {max_seq})")

            # Stop if we've reached the last page (seq didn't advance much)
            if max_seq < page * 50 - 10:
                print(f"  Reached end at page {page}.")
                break

            time.sleep(args.delay)

        except Exception as exc:
            print(f"  Page {page} error: {exc}")
            time.sleep(args.delay * 2)

    with open(args.out, "w") as f:
        json.dump(all_patents, f, indent=2, ensure_ascii=False)

    print(f"\nTotal unique patents: {len(all_patents)}")
    print(f"Saved to: {args.out}")


if __name__ == "__main__":
    main()
