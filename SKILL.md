---
name: patent-search
description: Search and retrieve patent lists for any company from public patent databases (FreePatentsOnline, Google Patents, Espacenet/EPO). Use when asked to search patents, look up a company's patent portfolio, find patents by assignee, retrieve patent counts, or compile patent lists for competitive analysis. Triggers on "搜索专利", "检索专利", "查专利", "patent search", "find patents for", "patent portfolio", "competitor patents", or any request to retrieve patents from a named company or keyword.
---

# Patent Search Skill

Search a company's patent portfolio from public databases and compile a categorized, deduplicated list.

## Workflow

1. **Search FreePatentsOnline** (main source, no auth required, paginates well)
2. **Supplement with Google Patents CSV** (catches recent/EP patents)
3. **Deduplicate and categorize** with the compile script
4. **Save output** as Markdown + CSV to workspace

## Scripts

### `scripts/fpo_search.py` — FreePatentsOnline bulk search
```
python3 scripts/fpo_search.py --assignee "MULTIVAC SEPP HAGGENMUELLER" --pages 10 --out /tmp/results.json
```
- Fetches all pages from FreePatentsOnline (US patent database)
- Returns JSON array: `[{id, title, abstract}, ...]`
- Rate-limit friendly: 1-second delay between pages

### `scripts/google_patents_csv.py` — Google Patents CSV export
```
python3 scripts/google_patents_csv.py --assignee "Multivac" --out /tmp/gp.csv
```
- Uses Google Patents XHR endpoint (no API key needed)
- Fetches by date range slices to bypass 20-result limit
- Falls back gracefully on 503 rate-limit

### `scripts/compile_patents.py` — Merge, deduplicate, categorize
```
python3 scripts/compile_patents.py --fpo /tmp/results.json --gp /tmp/gp.csv --out /tmp/output.md
```
- Merges all sources, deduplicates by patent number
- Auto-categorizes by title keywords (thermoforming / slicing / sealing / etc.)
- Outputs Markdown table + CSV

## Key Notes

- **FreePatentsOnline** is most reliable (no Cloudflare, paginates to 10+ pages × 50 results)
- **Google Patents** returns CSV via `https://patents.google.com/xhr/query?url=assignee%3D{name}`; rate-limits after ~3 rapid calls — space them out
- **Espacenet (EPO)** blocks automated access (403); use browser relay or manual export
- **EPO OPS API** requires registration token (free tier available at epo.org)
- Company name variants matter: search both `MULTIVAC SEPP HAGGENMUELLER` and `MULTIVAC SEPP HAGGENMÜLLER` and `Multivac Sepp Haggenmuller`

## Output Format

Saved to `workspace/<company>_patents_FULL.md`:
- Summary table (total / granted / applications / by category)
- Per-category sections with patent number, year, title, status
- Companion CSV for spreadsheet analysis

## References

- See `references/databases.md` for all supported databases and their limitations
- See `references/categories.md` for keyword-to-category mapping rules
