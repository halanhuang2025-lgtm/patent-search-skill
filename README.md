# 🔍 patent-search

> OpenClaw skill — Search, download, and analyze a company's patent portfolio from public databases. No API key required.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[中文文档](#中文说明)

---

## Overview

A complete 5-step pipeline from search to competitive analysis:

| Step | Script | What it does |
|------|--------|-------------|
| 1️⃣ Search | `fpo_search.py` | Bulk search FreePatentsOnline by assignee name |
| 2️⃣ Supplement | `google_patents_csv.py` | Export CSV from Google Patents (EP/recent coverage) |
| 3️⃣ Compile | `compile_patents.py` | Merge, deduplicate, auto-categorize → Markdown + CSV report |
| 4️⃣ Download | `download_patents.py` | Batch download PDFs via USPTO's free API |
| 5️⃣ Analyze | `process_patents.py` | Organize folders + extract abstracts/claims + relevance scoring |

**Tested on Multivac**: 466 patents retrieved, 465 PDFs downloaded (99.8% success), all abstracts extracted — in ~10 minutes.

---

## Quick Start

### Install dependencies

```bash
pip install pdfplumber pypdf
```

### Full pipeline

```bash
# 1. Search patent list
python3 scripts/fpo_search.py \
  --assignee "MULTIVAC SEPP HAGGENMUELLER" \
  --pages 12 \
  --out /tmp/patents.json

# 2. Generate categorized report
python3 scripts/compile_patents.py \
  --fpo /tmp/patents.json \
  --out ~/patents_report.md \
  --company "Multivac"

# 3. Batch download PDFs (10–30 min depending on count)
python3 scripts/download_patents.py \
  --input /tmp/patents.json \
  --outdir ~/Downloads/patents_pdf \
  --workers 3

# 4. Organize + extract + analyze
python3 scripts/process_patents.py \
  --pdf-dir ~/Downloads/patents_pdf \
  --fpo-json /tmp/patents.json \
  --out-dir ~/Downloads/patents_organized
```

---

## Scripts

### `fpo_search.py`

Searches [FreePatentsOnline](https://www.freepatentsonline.com) by assignee. No auth, no Cloudflare, paginates reliably.

```bash
python3 fpo_search.py --assignee <NAME> [--pages N] [--delay SEC] [--out FILE]
```

| Argument | Default | Description |
|----------|---------|-------------|
| `--assignee` | required | Assignee name (ALL CAPS works best) |
| `--pages` | 10 | Max pages to fetch (50 results/page) |
| `--delay` | 1.2 | Delay between requests (seconds) |
| `--out` | /tmp/fpo_patents.json | Output JSON path |

> **Tip**: Companies often have multiple name variants. Search `COMPANY NAME` and `COMPANY INC` separately and merge.

---

### `google_patents_csv.py`

Exports patent data from Google Patents via a hidden XHR/CSV endpoint. Better EP and recent patent coverage.

```bash
python3 google_patents_csv.py --assignee <NAME> [--delay SEC] [--out FILE]
```

> ⚠️ Google Patents rate-limits after ~3 rapid requests (HTTP 503). Use `--delay 2.0` to be safe.

---

### `compile_patents.py`

Merges sources, deduplicates, auto-categorizes by title keywords, and outputs a Markdown report + CSV.

```bash
python3 compile_patents.py --fpo <JSON> [--gp <CSV>] --out <MD> [--company <NAME>]
```

**15 auto-categories:**

| Category | Example keywords |
|----------|-----------------|
| Thermoforming | thermoform, deep draw, forming station |
| Tray Sealer | tray seal, tray sealer |
| Chamber Machine | chamber, vacuum bag |
| Slicing | slicer, blade, caliber |
| Smart/Digital | process param, bus node, predictive |
| … | See `references/categories.md` for full list |

---

### `download_patents.py`

Batch downloads patent PDFs. Resumes interrupted downloads automatically.

```bash
python3 download_patents.py \
  --input <JSON_or_CSV> \
  --outdir <DIR> \
  [--workers N] \
  [--delay SEC] \
  [--limit N]
```

| Argument | Default | Description |
|----------|---------|-------------|
| `--input` | required | JSON from fpo_search.py or CSV from compile |
| `--outdir` | /tmp/patents_pdf | Output directory for PDFs |
| `--workers` | 3 | Parallel download threads |
| `--delay` | 0.5 | Delay between requests (seconds) |
| `--limit` | 0 (all) | Max patents to download (for testing) |

**Source priority:**

1. 🥇 [USPTO image-ppubs](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/{id}) — primary, free, ~99% success
2. 🥈 Google Patents PDF — fallback
3. 🥉 Espacenet — for EP/WO patents

**Outputs:**
- `download_log.csv` — status for every patent
- `failed_ids.txt` — patents that failed (can be retried)

---

### `process_patents.py`

Three-in-one processor: organize into folders → extract text → relevance scoring.

```bash
python3 process_patents.py \
  --pdf-dir <PDF_DIR> \
  --fpo-json <JSON> \
  --out-dir <OUT_DIR> \
  [--keywords "term:weight,term:weight"] \
  [--no-extract]
```

| Argument | Description |
|----------|-------------|
| `--keywords` | Custom relevance keywords, e.g. `"tray seal:10,chamber:8"` |
| `--no-extract` | Skip PDF text extraction (faster, title-based scoring only) |

**Output structure:**
```
out-dir/
├── Thermoforming/          # PDFs organized by category
├── Tray_Sealer/
├── Chamber_Machine/
├── ...
├── all_extractions.json    # Abstract + top 3 claims per patent
└── RELEVANCE_REPORT.md     # Competitive analysis report
```

The relevance report includes:
- Patent count per technology area with risk level
- Top 30 scored patents (ranked by keyword match + category weight)
- Full detail (abstract, claims, link) for top 15
- High-risk patent checklist for legal review

---

## Data Sources

| Database | Coverage | Automation | Notes |
|----------|----------|------------|-------|
| FreePatentsOnline | US patents | ✅ Most reliable | No Cloudflare |
| Google Patents | Global (US/EP/WO/DE/JP/CN) | ⚠️ Rate-limited | Space requests 2s+ |
| USPTO image-ppubs | US patent PDFs | ✅ Official API | 99%+ success rate |
| Espacenet (EPO) | 140+ countries | ⚠️ Restricted | EP/WO PDFs only |
| PATENTSCOPE (WIPO) | PCT applications | ❌ JS-rendered | Manual only |

See `references/databases.md` for details.

---

## Using as an OpenClaw Skill

This repository is a standard [OpenClaw](https://github.com/openclaw/openclaw) AgentSkill:

```bash
# Install from ClawHub
clawhub install patent-search

# Or install locally
git clone https://github.com/halanhuang2025-lgtm/patent-search-skill.git
clawhub install ./patent-search-skill --local
```

Once installed, just tell OpenClaw:

> "Search patents for [company name], download all PDFs, and analyze which ones are relevant to our products"

---

## License

MIT

---

## 中文说明

### 功能

无需 API Key，从公开专利数据库批量检索、下载和分析指定公司的专利组合。

### 完整流程

```bash
# 1. 搜索专利列表
python3 scripts/fpo_search.py --assignee "公司英文名" --pages 12 --out /tmp/patents.json

# 2. 生成分类报告
python3 scripts/compile_patents.py --fpo /tmp/patents.json --out ~/report.md --company "公司名"

# 3. 批量下载 PDF（约 10-30 分钟）
python3 scripts/download_patents.py --input /tmp/patents.json --outdir ~/Downloads/patents --workers 3

# 4. 整理 + 提取摘要/权利要求 + 竞品分析
python3 scripts/process_patents.py --pdf-dir ~/Downloads/patents --fpo-json /tmp/patents.json --out-dir ~/Downloads/organized
```

### 关键特点

- **免费**：全部使用公开接口，无需付费订阅
- **高成功率**：USPTO image-ppubs 接口下载成功率 99%+
- **自动分类**：15 个技术领域自动归类
- **竞品分析**：可配置关键词权重，输出相关性评分报告
- **断点续传**：下载中断后重跑会自动跳过已存在文件
