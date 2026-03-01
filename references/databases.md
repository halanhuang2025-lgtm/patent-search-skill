# Patent Database Reference

## FreePatentsOnline (freepatentsonline.com)
- **Coverage**: US patents (grants + applications), some EP
- **Access**: Free, no auth, no Cloudflare
- **Search URL**: `https://www.freepatentsonline.com/result.html?p={PAGE}&num=50&srchtype=assignee&query_txt={NAME}&dbase=US`
- **Results per page**: 50
- **Typical depth**: 5–12 pages (250–600 results) for large companies
- **Reliability**: ✅ Best for automated access

## Google Patents
- **Coverage**: US, EP, WO, DE, JP, CN (most comprehensive)
- **Access**: Free, no auth, but rate-limits aggressive automated queries
- **CSV endpoint**: `https://patents.google.com/xhr/query?url=assignee%3D{NAME}&exp=&download=false`
- **Results**: ~20 per query; use date-range slicing to get more
- **Rate limit**: ~3 rapid calls before 503; wait 30s+ to recover
- **Reliability**: ✅ Good for supplements, ⚠️ unreliable for bulk

## Espacenet (EPO)
- **Coverage**: 140+ countries, EP and PCT filings
- **URL**: `https://worldwide.espacenet.com/patent/search?q=pa%3D{NAME}`
- **Access**: Blocks `web_fetch` (Cloudflare), needs browser relay
- **API (OPS)**: `https://ops.epo.org/` — requires free registration token
- **Reliability**: ✅ Manual use, ⚠️ automated access blocked

## PATENTSCOPE (WIPO)
- **Coverage**: PCT international applications (126M documents)
- **URL**: `https://patentscope.wipo.int/search/en/search.jsf?query=PA%3A{NAME}`
- **Access**: JS-rendered, no direct API without registration
- **Reliability**: ⚠️ JS-heavy, manual only

## PatSnap / Derwent (commercial)
- **Coverage**: Full global coverage with analytics
- **Access**: Paid subscription
- **Use when**: Need complete DE/JP/CN coverage or patent analytics

## Tips for Company Name Variants
Always search multiple name variants:
- Full legal name: `MULTIVAC SEPP HAGGENMUELLER SE & CO. KG`
- Short name: `MULTIVAC SEPP HAGGENMUELLER`
- Old name: `MULTIVAC SEPP HAGGENMUELLER GMBH & CO. KG`
- Short: `Multivac`

Umlaut handling: search both `HAGGENMÜLLER` and `HAGGENMUELLER` (FPO normalizes, Google may not).
