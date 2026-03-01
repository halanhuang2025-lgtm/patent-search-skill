#!/usr/bin/env python3
"""
Batch download patent PDFs from USPTO / Google Patents / EPO.
Usage:
  python3 download_patents.py --input /tmp/fpo.json --outdir /tmp/patents_pdf/
  python3 download_patents.py --input /tmp/fpo.json --outdir /tmp/patents_pdf/ --workers 3

Sources tried in order per patent:
  1. Google Patents PDF redirect
  2. USPTO PDFPIW (granted US only)
  3. USPTO AppFT (applications only)
  4. EPO Espacenet (EP/WO)
"""

import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/pdf,*/*",
    "Referer": "https://patents.google.com/",
}


# ──────────────────────────────────────────
# ID normalisation helpers
# ──────────────────────────────────────────

def normalise_id(raw: str) -> str:
    """Return a canonical patent ID string."""
    return raw.strip().upper().replace(" ", "")


def is_us_granted(pid: str) -> bool:
    """True for bare numeric (7-digit+) or US<digits> without trailing A-letter."""
    if re.match(r"^\d{7,10}$", pid):
        return True
    if re.match(r"^US\d{7,10}$", pid) and not re.search(r"A\d$", pid):
        return True
    if re.search(r"B[12]$", pid):
        return True
    return False


def is_us_application(pid: str) -> bool:
    return bool(re.match(r"^US2\d{9}$", pid) or re.search(r"A[123]$", pid))


def is_ep(pid: str) -> bool:
    return pid.startswith("EP")


def is_wo(pid: str) -> bool:
    return pid.startswith("WO")


def pad_us_number(pid: str) -> str:
    """Convert '8825569' or 'US8825569' → '08825569' for USPTO."""
    num = re.sub(r"^US", "", pid)
    num = re.sub(r"[A-Z]\d$", "", num)   # strip B2 etc.
    return num.zfill(8)


# ──────────────────────────────────────────
# Download URL builders
# ──────────────────────────────────────────

def uspub_pdf_url(pid: str) -> str:
    """USPTO image-ppubs (primary, works for granted + applications)."""
    num = re.sub(r"^US", "", pid)
    num = re.sub(r"[A-Z]\d?$", "", num)   # strip B2, A1 etc.
    return f"https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/{num}"


def google_pdf_url(pid: str) -> str:
    """Google Patents PDF (fallback)."""
    if re.match(r"^\d{7,10}$", pid):
        pid = "US" + pid
    return f"https://patents.google.com/patent/{pid}/pdf"


def ep_pdf_url(pid: str) -> str:
    """EPO Espacenet PDF."""
    return f"https://worldwide.espacenet.com/patent/{pid}/pdf"


# ──────────────────────────────────────────
# Core download function
# ──────────────────────────────────────────

def download_patent(pid: str, out_path: Path, timeout: int = 30) -> tuple[str, bool, str]:
    """
    Try to download one patent PDF.
    Returns (pid, success, message).
    """
    if out_path.exists() and out_path.stat().st_size > 5000:
        return pid, True, "already exists"

    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Build candidate URLs — USPTO image-ppubs is primary for US patents
    urls = []
    if is_ep(pid) or is_wo(pid):
        urls = [ep_pdf_url(pid), google_pdf_url(pid)]
    else:
        urls = [uspub_pdf_url(pid), google_pdf_url(pid)]

    for url in urls:
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                content_type = resp.headers.get("Content-Type", "")
                data = resp.read()

                # Validate it's a PDF (starts with %PDF)
                if data[:4] == b"%PDF" or b"%PDF" in data[:50]:
                    out_path.write_bytes(data)
                    return pid, True, f"ok ({len(data)//1024}KB) via {url[:50]}"
                else:
                    continue   # Not a PDF, try next URL
        except Exception as e:
            continue   # Try next URL

    return pid, False, f"failed all {len(urls)} sources"


# ──────────────────────────────────────────
# Main
# ──────────────────────────────────────────

def load_ids(path: str) -> list[dict]:
    """Load patents from JSON (fpo_search output) or CSV (compile output)."""
    if path.endswith(".json"):
        with open(path) as f:
            data = json.load(f)
        return [{"id": p["id"], "title": p.get("title", ""), "category": p.get("category", "")} for p in data]
    else:  # CSV
        rows = []
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                pid = row.get("Patent_No", row.get("id", "")).strip('"')
                rows.append({"id": pid, "title": row.get("Title", row.get("title", "")),
                             "category": row.get("Category", row.get("category", ""))})
        return rows


def main():
    parser = argparse.ArgumentParser(description="Batch download patent PDFs")
    parser.add_argument("--input",   required=True, help="JSON or CSV patent list")
    parser.add_argument("--outdir",  default="/tmp/patents_pdf", help="Output directory")
    parser.add_argument("--workers", type=int, default=3, help="Parallel download workers")
    parser.add_argument("--delay",   type=float, default=0.5, help="Delay between requests (s)")
    parser.add_argument("--limit",   type=int, default=0, help="Max patents to download (0=all)")
    args = parser.parse_args()

    patents = load_ids(args.input)
    if args.limit:
        patents = patents[:args.limit]

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    print(f"Downloading {len(patents)} patents → {outdir}")
    print(f"Workers: {args.workers} | Delay: {args.delay}s\n")

    results = {"ok": [], "fail": [], "skip": []}
    log_path = outdir / "download_log.csv"

    with open(log_path, "w", newline="", encoding="utf-8") as logf:
        log_writer = csv.writer(logf)
        log_writer.writerow(["patent_id", "title", "status", "message", "file"])

        def job(p: dict):
            pid = normalise_id(p["id"])
            category = re.sub(r"[^\w]", "_", p.get("category", "other"))
            fname = re.sub(r"[^\w\-]", "_", pid) + ".pdf"
            fpath = outdir / category / fname
            time.sleep(args.delay)
            return p, *download_patent(pid, fpath)

        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futures = {ex.submit(job, p): p for p in patents}
            done = 0
            for fut in as_completed(futures):
                done += 1
                try:
                    p, pid, ok, msg = fut.result()
                except Exception as e:
                    pid, ok, msg = futures[fut]["id"], False, str(e)
                    p = futures[fut]

                status = "ok" if ok else ("skip" if "already" in msg else "fail")
                results[status if status in results else "fail"].append(pid)

                category = p.get("category", "")
                fname = re.sub(r"[^\w\-]", "_", normalise_id(pid)) + ".pdf"
                fpath = outdir / re.sub(r"[^\w]", "_", category) / fname

                icon = "✅" if ok else "❌"
                print(f"[{done:3d}/{len(patents)}] {icon} {pid:<20} {msg}")
                log_writer.writerow([pid, p.get("title","")[:80], status, msg, str(fpath)])
                logf.flush()

    print(f"\n{'='*50}")
    print(f"Downloaded: {len(results['ok'])} ✅")
    print(f"Failed:     {len(results['fail'])} ❌")
    print(f"Skipped:    {len(results['skip'])} (already existed)")
    print(f"Log:        {log_path}")

    # Size summary
    total_bytes = sum(f.stat().st_size for f in outdir.rglob("*.pdf") if f.is_file())
    print(f"Total size: {total_bytes//1024//1024} MB")

    if results["fail"]:
        fail_path = outdir / "failed_ids.txt"
        fail_path.write_text("\n".join(results["fail"]))
        print(f"Failed IDs: {fail_path}")

    return 0 if not results["fail"] else 1


if __name__ == "__main__":
    sys.exit(main())
