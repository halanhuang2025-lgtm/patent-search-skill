# 🔍 patent-search

> OpenClaw skill — 从公开数据库批量检索、下载和分析公司专利组合

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 功能概览

| 步骤 | 脚本 | 功能 |
|------|------|------|
| 1️⃣ 搜索 | `fpo_search.py` | FreePatentsOnline 按申请人批量抓取 |
| 2️⃣ 补充 | `google_patents_csv.py` | Google Patents CSV 导出，补充 EP/近期专利 |
| 3️⃣ 整理 | `compile_patents.py` | 合并去重 + 自动分类 → Markdown + CSV 报告 |
| 4️⃣ 下载 | `download_patents.py` | 批量下载 PDF（USPTO 官方接口，免费） |
| 5️⃣ 分析 | `process_patents.py` | 整理文件夹 + 提取摘要/权利要求 + 相关性评分 |

**实测数据（Multivac 公司）**：466 件专利，465 件 PDF 下载成功（99.8%），全部摘要提取成功，耗时约 10 分钟。

---

## 快速上手

### 安装依赖

```bash
pip install pdfplumber pypdf
```

### 完整流程

```bash
# 1. 搜索专利列表
python3 scripts/fpo_search.py \
  --assignee "MULTIVAC SEPP HAGGENMUELLER" \
  --pages 12 \
  --out /tmp/patents.json

# 2. 生成分类报告
python3 scripts/compile_patents.py \
  --fpo /tmp/patents.json \
  --out ~/patents_report.md \
  --company "Multivac"

# 3. 批量下载 PDF（~10-30 分钟，视专利数量）
python3 scripts/download_patents.py \
  --input /tmp/patents.json \
  --outdir ~/Downloads/patents_pdf \
  --workers 3

# 4. 整理 + 提取 + 分析
python3 scripts/process_patents.py \
  --pdf-dir ~/Downloads/patents_pdf \
  --fpo-json /tmp/patents.json \
  --out-dir ~/Downloads/patents_organized
```

---

## 各脚本说明

### `fpo_search.py`

从 [FreePatentsOnline](https://www.freepatentsonline.com) 按申请人名称批量检索美国专利。

```
python3 fpo_search.py --assignee <NAME> [--pages N] [--delay SEC] [--out FILE]
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--assignee` | 必填 | 申请人名称（全大写效果更好） |
| `--pages` | 10 | 最大抓取页数（每页 50 条） |
| `--delay` | 1.2 | 请求间隔（秒），避免被封 |
| `--out` | /tmp/fpo_patents.json | 输出 JSON 路径 |

> **提示**：公司名有多种写法时，建议分别搜索后合并，例如 `MULTIVAC SEPP HAGGENMUELLER` 和 `Multivac`。

---

### `google_patents_csv.py`

通过 Google Patents 隐藏 CSV 接口导出专利数据，覆盖 EP、WO、近期专利。

```
python3 google_patents_csv.py --assignee <NAME> [--delay SEC] [--out FILE]
```

> ⚠️ Google Patents 有速率限制，连续请求超过 3 次会返回 503，建议 `--delay 2.0`。

---

### `compile_patents.py`

合并多个来源，去重，按技术领域自动分类，输出 Markdown 报告和 CSV。

```
python3 compile_patents.py --fpo <JSON> [--gp <CSV>] --out <MD> [--company <NAME>]
```

**自动分类（15 个领域）**：

| 领域 | 关键词示例 |
|------|-----------|
| Thermoforming | thermoform, deep draw, forming station |
| Tray Sealer | tray seal, tray sealer |
| Chamber Machine | chamber, vacuum bag |
| Slicing | slicer, blade, caliber |
| Smart/Digital | process param, bus node, predictive |
| … | 详见 `references/categories.md` |

---

### `download_patents.py`

批量从 USPTO 下载专利 PDF，支持断点续传。

```
python3 download_patents.py --input <JSON_or_CSV> --outdir <DIR> [--workers N] [--delay SEC] [--limit N]
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--input` | 必填 | fpo_search.py 的 JSON 或 compile 的 CSV |
| `--outdir` | /tmp/patents_pdf | PDF 保存目录 |
| `--workers` | 3 | 并发下载线程数 |
| `--delay` | 0.5 | 请求间隔（秒） |
| `--limit` | 0（全部）| 限制下载数量（测试用） |

**下载来源优先级**：

1. 🥇 [USPTO image-ppubs](https://image-ppubs.uspto.gov) — 主力，免费，稳定
2. 🥈 Google Patents PDF — 备用
3. 🥉 Espacenet — EP/WO 专利

下载完成后输出：
- `download_log.csv` — 每件专利的下载状态
- `failed_ids.txt` — 失败列表（可重试）

---

### `process_patents.py`

三合一处理器：整理文件夹 → 提取文本 → 竞品相关性分析。

```
python3 process_patents.py \
  --pdf-dir <PDF目录> \
  --fpo-json <JSON> \
  --out-dir <输出目录> \
  [--keywords "term:weight,term:weight"] \
  [--no-extract]
```

| 参数 | 说明 |
|------|------|
| `--keywords` | 自定义相关性关键词，格式 `"tray seal:10,chamber:8"` |
| `--no-extract` | 跳过 PDF 文本提取，只做整理和标题级评分 |

**输出**：
```
out-dir/
├── Thermoforming/          # 按类别整理的 PDF
├── Tray_Sealer/
├── Chamber_Machine/
├── ...
├── all_extractions.json    # 每件专利的摘要 + 权利要求
└── RELEVANCE_REPORT.md     # 竞品相关性分析报告
```

---

## 数据来源说明

| 数据库 | 覆盖范围 | 自动化支持 | 备注 |
|--------|---------|-----------|------|
| FreePatentsOnline | 美国专利 | ✅ 最稳定 | 无 Cloudflare |
| Google Patents | 全球（US/EP/WO/DE/JP/CN）| ⚠️ 有速率限制 | 建议间隔 2s |
| USPTO image-ppubs | 美国专利 PDF | ✅ 官方接口 | 99%+ 成功率 |
| Espacenet (EPO) | 全球 140+ 国 | ⚠️ 限制较多 | EP/WO 专利 PDF |
| PATENTSCOPE (WIPO) | PCT 国际申请 | ❌ JS 渲染 | 建议手动 |

> 详细说明见 `references/databases.md`

---

## 作为 OpenClaw Skill 使用

本仓库是一个标准 OpenClaw AgentSkill，可直接安装：

```bash
# 方式一：从 .skill 文件安装
clawhub install patent-search

# 方式二：克隆后本地安装
git clone https://github.com/halanhuang2025-lgtm/patent-search-skill.git
clawhub install ./patent-search-skill --local
```

安装后，直接对 OpenClaw 说：

> "帮我检索一下 [公司名] 的专利，全部下载下来，然后分析哪些跟我们产品相关"

---

## License

MIT
