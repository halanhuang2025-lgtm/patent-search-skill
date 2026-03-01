#!/usr/bin/env python3
"""
Three-in-one patent processor:
  1. Organize PDFs into category folders
  2. Extract abstracts + claims from each PDF via pdfplumber
  3. Score relevance to a target company profile

Usage:
  python3 process_patents.py \
    --pdf-dir ~/Downloads/co_patents \
    --fpo-json /tmp/co.json \
    --out-dir ~/Downloads/co_organized \
    [--keywords "tray seal:10,chamber:8,vacuum bag:8"]

Dependencies: pip install pdfplumber pypdf
"""

import argparse, csv, json, os, re, shutil
from collections import defaultdict
from pathlib import Path


def parse_args():
    p = argparse.ArgumentParser(description="Organize, extract, and analyze patent PDFs")
    p.add_argument("--pdf-dir",  default=str(Path.home()/"Downloads/multivac_patents_pdf"),
                   help="Directory containing downloaded PDF files")
    p.add_argument("--fpo-json", default="/tmp/multivac_fpo_full.json",
                   help="JSON output from fpo_search.py")
    p.add_argument("--out-dir",  default=str(Path.home()/"Downloads/multivac_patents_organized"),
                   help="Output directory for organized files + reports")
    p.add_argument("--keywords", default="",
                   help='Custom relevance keywords: "term:weight,term:weight" '
                        '(overrides built-in packaging machinery keywords)')
    p.add_argument("--no-extract", action="store_true",
                   help="Skip PDF text extraction (faster, only title-based scoring)")
    return p.parse_args()


args = parse_args()

try:
    import pdfplumber
    HAS_PDF = True
except ImportError:
    HAS_PDF = False
    print("⚠️  pdfplumber not available")

# ─────────────────────────────────────
# Config (from args)
# ─────────────────────────────────────
PDF_DIR   = Path(args.pdf_dir)
FPO_JSON  = Path(args.fpo_json)
OUT_DIR   = Path(args.out_dir)
REPORT_MD = OUT_DIR / "RELEVANCE_REPORT.md"

# Default relevance keywords (packaging machinery / 包装机)
# Override with --keywords "term:weight,term:weight"
HUANLIAN_WEIGHT = {
    "tray seal": 10, "tray sealer": 10, "tray sealing machine": 10,
    "chamber": 8, "vacuum chamber": 9, "vacuum bag": 8,
    "undergripper": 7, "tray gripper": 7, "gripper arm": 6,
    "thermoform": 6, "deep draw": 6, "deep-draw": 6,
    "evacuat": 5, "gas flush": 5, "modified atmosphere": 5,
    "sealing station": 5, "cover film": 4, "lid film": 4,
    "cutting station": 3, "film punch": 3, "gas concentration": 4,
}

CATEGORY_RULES = [
    ("Slicing",          r"slic|slicing|knife|knives|blade|cutter unit|caliber"),
    ("Thermoforming",    r"thermoform|deep.draw|deep draw|forming station|deep-draw"),
    ("Tray Sealer",      r"tray seal|tray sealer|tray-seal"),
    ("Chamber Machine",  r"chamber|vacuum bag|bag seal|bulk goods.*bag"),
    ("Sealing",          r"\bseal(ing)?\b"),
    ("Cutting",          r"\bcut(ting)?\s+station|complete.cut|punching device"),
    ("Automation/Robot", r"robot|picker|gripper|pick.and.place|loading station"),
    ("Conveying",        r"convey|transport|transfer|lane divid|race track"),
    ("Smart/Digital",    r"process param|bus node|digital|smart|predictiv|recipe"),
    ("High-pressure",    r"high.pressure|HPP"),
    ("Sustainable",      r"paper material|cardboard|fiber.contain|reclosable"),
    ("Auxiliary",        r"winder|nozzle|suction|mandrel|mounting plate|valve"),
    ("Packaging",        r"reclosable package|liquid.*package"),
]

def categorize(title):
    t = title.lower()
    for cat, pattern in CATEGORY_RULES:
        if re.search(pattern, t):
            return cat
    return "Other"

# ─────────────────────────────────────
# STEP 1: Load metadata
# ─────────────────────────────────────
print("=" * 55)
print("STEP 1: Loading metadata...")

with open(FPO_JSON) as f:
    fpo_data = json.load(f)

meta = {}
for p in fpo_data:
    pid = p["id"].strip().upper()
    title = p.get("title", "")
    cat = categorize(title)
    fname = re.sub(r"[^\w\-]", "_", pid) + ".pdf"
    meta[pid] = {"title": title, "category": cat, "fname": fname}

pdf_files = list(PDF_DIR.glob("*.pdf"))
print(f"  {len(meta)} patents in index | {len(pdf_files)} PDFs on disk")

fname_to_meta = {}
for pid, m in meta.items():
    fname_to_meta[m["fname"]] = (pid, m)

# ─────────────────────────────────────
# STEP 2: Organize into folders
# ─────────────────────────────────────
print("\n" + "=" * 55)
print("STEP 2: Organizing into category folders...")
OUT_DIR.mkdir(parents=True, exist_ok=True)
moved = defaultdict(int)

for pdf in pdf_files:
    fname = pdf.name
    entry = fname_to_meta.get(fname)
    if not entry:
        pid_raw = fname.replace(".pdf","").replace("_","").upper()
        for k, v in fname_to_meta.items():
            if k.replace("_","").upper() == pid_raw:
                entry = v
                break
    cat = entry[1]["category"] if entry else "Other"
    cat_safe = re.sub(r"[^\w\-]", "_", cat)
    dest_dir = OUT_DIR / cat_safe
    dest_dir.mkdir(exist_ok=True)
    dest = dest_dir / fname
    if not dest.exists():
        shutil.copy2(pdf, dest)
    moved[cat] += 1

print(f"  Organized into {len(moved)} folders:")
for cat, cnt in sorted(moved.items(), key=lambda x: -x[1]):
    cat_safe = re.sub(r"[^\w\-]", "_", cat)
    size = sum(f.stat().st_size for f in (OUT_DIR/cat_safe).glob("*.pdf"))
    print(f"    {cat:25s} {cnt:3d} files  {size//1024//1024}MB")

# ─────────────────────────────────────
# STEP 3: Extract text
# ─────────────────────────────────────
print("\n" + "=" * 55)
print("STEP 3: Extracting abstracts + claims...")

def extract_sections(pdf_path):
    try:
        with pdfplumber.open(pdf_path) as pdf:
            full_text = "".join(
                (page.extract_text() or "") + "\n"
                for page in pdf.pages[:15]
            )
    except Exception as e:
        return None, None

    # Abstract
    abstract = ""
    m = re.search(
        r'ABSTRACT\s*\n+(.*?)(?=\n(?:CLAIMS?|BRIEF DESCRIPTION|BACKGROUND|FIELD OF|SUMMARY|\d+\s*\n\s*\d+))',
        full_text, re.DOTALL | re.IGNORECASE)
    if m:
        abstract = re.sub(r'\s+', ' ', m.group(1)).strip()[:1500]

    # Claims (first 3)
    claims = ""
    m2 = re.search(
        r'(?:^|\n)CLAIMS?\s*\n+(.*?)(?=\n(?:ABSTRACT|DESCRIPTION OF THE DRAWINGS|\Z))',
        full_text, re.DOTALL | re.IGNORECASE)
    if not m2:
        m2 = re.search(r'What is claimed.*?:\s*\n+(.*)', full_text, re.DOTALL | re.IGNORECASE)
    if m2:
        blocks = re.split(r'\n\s*\d{1,2}\s*\.', m2.group(1).strip())
        claims = " | ".join(
            f"{i+1}. {re.sub(chr(10), ' ', b).strip()[:300]}"
            for i, b in enumerate(blocks[:3]) if b.strip()
        )[:2000]

    return abstract, claims

extractions = {}
errors = 0
# Parse custom keywords if provided
if args.keywords:
    HUANLIAN_WEIGHT.clear()
    for pair in args.keywords.split(","):
        parts = pair.strip().split(":")
        if len(parts) == 2:
            HUANLIAN_WEIGHT[parts[0].strip()] = int(parts[1].strip())

if HAS_PDF and not args.no_extract:
    for i, pdf in enumerate(sorted(pdf_files)):
        fname = pdf.name
        entry = fname_to_meta.get(fname)
        if not entry:
            pid_raw = fname.replace(".pdf","").replace("_","").upper()
            for k, v in fname_to_meta.items():
                if k.replace("_","").upper() == pid_raw:
                    entry = v; break
        pid   = entry[0] if entry else fname.replace(".pdf","")
        mdata = entry[1] if entry else {"title": fname, "category": "Other"}

        abstract, claims = extract_sections(pdf)
        if abstract is None:
            errors += 1
        else:
            extractions[pid] = {
                "title":    mdata.get("title",""),
                "category": mdata.get("category",""),
                "abstract": abstract,
                "claims":   claims or "",
            }
        if (i+1) % 100 == 0:
            print(f"  [{i+1}/{len(pdf_files)}] {len(extractions)} ok / {errors} err")

    print(f"  Done: {len(extractions)} extracted, {errors} errors")
    extract_json = OUT_DIR / "all_extractions.json"
    with open(extract_json, "w", encoding="utf-8") as f:
        json.dump(extractions, f, indent=2, ensure_ascii=False)
    print(f"  Saved: {extract_json}")
else:
    if args.no_extract:
        print("  Skipped (--no-extract flag set)")
    else:
        print("  Skipped (install pdfplumber: pip install pdfplumber)")
    extractions = {}

# ─────────────────────────────────────
# STEP 4: Relevance scoring
# ─────────────────────────────────────
print("\n" + "=" * 55)
print("STEP 4: Scoring relevance for 华联机械...")

def score_patent(title, abstract, claims):
    text = (title + " " + abstract + " " + claims).lower()
    score = 0
    matched = []
    for kw, weight in HUANLIAN_WEIGHT.items():
        if re.search(kw, text):
            score += weight
            matched.append(kw)
    cat = categorize(title)
    if cat in ("Tray Sealer", "Chamber Machine"):   score += 15
    elif cat in ("Sealing", "Thermoforming"):        score += 8
    return score, matched, cat

scored = []
for pid, data in extractions.items():
    score, matched, cat = score_patent(
        data.get("title",""), data.get("abstract",""), data.get("claims",""))
    if score > 0:
        scored.append({"id": pid, **data, "score": score, "keywords": matched, "category": cat})

# Title-only for patents without extraction
for pid, m in meta.items():
    if pid not in extractions:
        score, matched, cat = score_patent(m["title"], "", "")
        if score > 5:
            scored.append({"id": pid, "title": m["title"], "category": cat,
                           "abstract":"(not extracted)", "claims":"",
                           "score": score, "keywords": matched})

scored.sort(key=lambda x: -x["score"])
high_risk = [p for p in scored if p["score"] >= 20 and p["category"] in ("Tray Sealer","Chamber Machine")]
print(f"  Relevant patents: {len(scored)}")
print(f"  High-risk (≥20, direct competition): {len(high_risk)}")

# ─────────────────────────────────────
# STEP 5: Write report
# ─────────────────────────────────────
print("\n" + "=" * 55)
print("STEP 5: Writing report...")

with open(REPORT_MD, "w", encoding="utf-8") as f:
    f.write("# Multivac 专利 × 华联机械相关性分析报告\n\n")
    f.write("> 生成时间：2026-03-01 | 分析专利：465 件\n\n")
    f.write("## 华联机械产品 → Multivac 专利对照\n\n")
    f.write("| 华联产品 | Multivac 专利方向 | 风险等级 |\n")
    f.write("|---------|-----------------|--------|\n")
    f.write("| 盒式真空包装机 | Tray Sealer | 🔴 高 |\n")
    f.write("| 真空包装机 | Chamber Machine | 🔴 高 |\n")
    f.write("| 热成型包装机 | Thermoforming | 🟡 中 |\n")
    f.write("| 密封机构 | Sealing | 🟡 中 |\n")
    f.write("| 自动化输送 | Automation/Robot | 🟢 低 |\n\n")
    f.write("---\n\n")

    # Category summary
    cat_counts = defaultdict(int)
    for p in scored:
        cat_counts[p["category"]] += 1
    f.write("## 相关专利数量分布\n\n")
    f.write("| 技术领域 | 数量 | 风险 |\n|---------|------|------|\n")
    for cat, cnt in sorted(cat_counts.items(), key=lambda x: -x[1]):
        risk = {"Tray Sealer":"🔴 高直接竞争","Chamber Machine":"🔴 高直接竞争",
                "Thermoforming":"🟡 技术参考","Sealing":"🟡 机构参考"}.get(cat,"🟢 参考")
        f.write(f"| {cat} | {cnt} | {risk} |\n")

    f.write("\n---\n\n")
    f.write(f"## Top 30 相关专利（评分排序）\n\n")
    f.write("| # | 专利号 | 评分 | 领域 | 标题 |\n|---|-------|------|------|------|\n")
    for i, p in enumerate(scored[:30], 1):
        title = p["title"][:65]+"…" if len(p["title"])>65 else p["title"]
        f.write(f"| {i} | `{p['id']}` | **{p['score']}** | {p['category']} | {title} |\n")

    f.write("\n---\n\n## 重点专利详情（Top 15）\n\n")
    for i, p in enumerate(scored[:15], 1):
        f.write(f"### {i}. `{p['id']}`（评分 {p['score']}）\n\n")
        f.write(f"**{p['title']}**\n\n")
        f.write(f"- **领域**: {p['category']}\n")
        f.write(f"- **匹配词**: {', '.join(p['keywords'])}\n")
        f.write(f"- **链接**: https://patents.google.com/patent/{p['id']}\n\n")
        if p.get("abstract") and p["abstract"] != "(not extracted)":
            ab = p["abstract"][:500]
            f.write(f"**摘要**: {ab}\n\n")
        if p.get("claims"):
            f.write(f"**主权利要求**:\n```\n{p['claims'][:600]}\n```\n\n")
        f.write("---\n\n")

    f.write("## 高风险专利清单（需法律评审）\n\n")
    f.write(f"> 共 {len(high_risk)} 件，建议委托知识产权律师审查权利要求范围\n\n")
    for p in high_risk:
        f.write(f"- [ ] `{p['id']}` — {p['title'][:70]}\n")
    f.write("\n\n> ⚠️ 本报告仅供参考，侵权判定需专业法律意见。\n")

print(f"\n{'='*55}")
print("✅ ALL DONE!")
print(f"{'='*55}")
print(f"📂 Organized folders : {OUT_DIR}/")
print(f"📄 Extractions JSON  : {OUT_DIR}/all_extractions.json")
print(f"🎯 Relevance report  : {REPORT_MD}")
print(f"   Relevant patents  : {len(scored)}")
print(f"   High-risk (≥20)   : {len(high_risk)}")
total_size = sum(f.stat().st_size for f in OUT_DIR.rglob("*.pdf"))
print(f"   Total PDF size    : {total_size//1024//1024}MB")
