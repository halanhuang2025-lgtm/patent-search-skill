---
name: patent-search
description: Search, download, and analyze company patent portfolios from public databases (FreePatentsOnline, Google Patents, USPTO). Use when asked to search patents, retrieve a company's patent list, download patent PDFs in bulk, extract abstracts and claims, or perform competitive patent analysis. Triggers on "搜索专利", "检索专利", "查专利", "下载专利", "patent search", "find patents for", "download patents", "patent portfolio", "competitor patents", "专利分析", or any request to retrieve/download/analyze patents for a named company.
---

# Patent Search Skill

End-to-end pipeline: search → download PDFs → extract text → competitive analysis.

## Full Workflow

```
fpo_search.py          →  patent ID list (JSON)
google_patents_csv.py  →  supplement with EP/recent (CSV)
compile_patents.py     →  merge + categorize → Markdown + CSV report
download_patents.py    →  batch download all PDFs from USPTO
process_patents.py     →  organize folders + extract abstracts/claims + relevance scoring
```

## Scripts

### 1. `fpo_search.py` — Bulk search FreePatentsOnline
```bash
python3 fpo_search.py --assignee "MULTIVAC SEPP HAGGENMUELLER" --pages 12 --out /tmp/patents.json
```
- No auth, no Cloudflare, 50 results/page, auto-stops at last page
- Output: JSON `[{id, title, seq}, ...]`

### 2. `google_patents_csv.py` — Google Patents supplement
```bash
python3 google_patents_csv.py --assignee "Multivac" --out /tmp/gp.csv --delay 2.0
```
- Date-range slicing to bypass 20-result limit
- Output: CSV with priority_date, grant_date, link

### 3. `compile_patents.py` — Merge, deduplicate, categorize
```bash
python3 compile_patents.py --fpo /tmp/patents.json --gp /tmp/gp.csv \
  --out ~/patents_report.md --company "Multivac"
```
- Auto-categorizes by title keywords (15 categories)
- Output: Markdown report + companion CSV

### 4. `download_patents.py` — Batch PDF download
```bash
python3 download_patents.py \
  --input /tmp/patents.json \
  --outdir ~/Downloads/patents_pdf \
  --workers 3 \
  --delay 0.4
```
- Primary source: **USPTO image-ppubs API** (`image-ppubs.uspto.gov`) — free, reliable
- Fallback: Google Patents PDF endpoint
- EP/WO: Espacenet
- Outputs `download_log.csv` + `failed_ids.txt`
- Resumes interrupted downloads (skips existing files)

### 5. `process_patents.py` — Organize + Extract + Analyze
```bash
python3 process_patents.py
# Edit config vars at top of script before running:
#   PDF_DIR  = path to downloaded PDFs
#   FPO_JSON = path to fpo_search output
#   OUT_DIR  = output directory
```
Three phases in one run:
- **Organize**: copies PDFs into category subfolders
- **Extract**: pulls Abstract + first 3 Claims from each PDF via pdfplumber
- **Score**: scores each patent for relevance to a target product profile
- Outputs: organized folders + `all_extractions.json` + `RELEVANCE_REPORT.md`

**Dependencies**: `pip install pdfplumber pypdf`

## Typical Run (new company)

```bash
# 1. Search
python3 fpo_search.py --assignee "COMPANY NAME" --pages 15 --out /tmp/co.json

# 2. Compile report
python3 compile_patents.py --fpo /tmp/co.json --out ~/co_patents.md --company "Company"

# 3. Download all PDFs (takes 10-30 min for 400+ patents)
python3 download_patents.py --input /tmp/co.json --outdir ~/Downloads/co_patents --workers 3

# 4. Process: organize + extract + analyze
# Edit PDF_DIR / FPO_JSON / OUT_DIR in process_patents.py first
python3 process_patents.py
```

## Key Notes

- FreePatentsOnline only covers **US patents**; search both `COMPANY NAME` and `COMPANY INC` variants
- Google Patents rate-limits after ~3 rapid calls; `--delay 2.0` is safe
- USPTO image-ppubs is the most reliable free PDF source (99%+ success rate)
- Withdrawn patents will always fail download — expected
- `process_patents.py` relevance keywords are tuned for packaging machinery; edit `HUANLIAN_WEIGHT` dict for different industries

## References

- See `references/databases.md` for all supported databases and limitations
- See `references/categories.md` for keyword-to-category mapping rules
