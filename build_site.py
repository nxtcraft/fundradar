"""Build SEO-optimized static site for FundRadar GitHub Pages."""

import json
from datetime import datetime, timezone
from pathlib import Path

DATA_FILE = Path("data/latest_funding.json")
DIST_DIR = Path("dist")
RAPIDAPI_URL = "https://rapidapi.com/PradeepKumarKesharwani/api/fundradar"
GITHUB_URL = "https://github.com/nxtcraft/fundradar"


def load_leads():
    with open(DATA_FILE, encoding="utf-8") as f:
        return json.load(f)


def fmt_usd(v):
    if not v:
        return None
    if v >= 1_000_000_000:
        return f"${v/1_000_000_000:.1f}B"
    if v >= 1_000_000:
        return f"${v/1_000_000:.0f}M"
    return f"${v/1_000:.0f}K"


def build_index(leads):
    updated = datetime.now(timezone.utc).strftime("%B %d, %Y at %H:%M UTC")
    funded = [l for l in leads if l.get("amount_usd")]
    total_vc = sum(l["amount_usd"] for l in funded)
    industries = sorted({l.get("industry", "Other") for l in leads if l.get("industry")})
    stages = sorted({l.get("round_type", "") for l in leads if l.get("round_type")})

    schema = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": "Startup Funding Intelligence — FundRadar",
        "description": f"Track {len(leads)} recently funded startups with round sizes, stages, and industry data.",
        "url": "https://nxtcraft.github.io/fundradar",
    }

    ind_buttons = "".join(
        f'<button class="f-btn" onclick="filterInd(\'{i}\')">{i}</button>'
        for i in industries
    )
    stage_buttons = "".join(
        f'<button class="f-btn" onclick="filterStage(\'{s}\')">{s}</button>'
        for s in stages if s
    )

    STAGE_COLOR = {
        "Seed": "#3fb950", "Series A": "#58a6ff", "Series B": "#bc8cff",
        "Series C": "#d29922", "Growth": "#f78166", "IPO": "#e3b341",
    }

    cards = ""
    for l in leads:
        amt = l.get("amount_usd")
        amt_str = fmt_usd(amt) or "Undisclosed"
        stage = l.get("round_type", "Unknown")
        sc = STAGE_COLOR.get(stage, "#8b949e")
        ind = l.get("industry", "Other")
        company = l.get("company_name", "Unknown")
        date_str = l.get("announced_date", "")[:10]
        summary = l.get("summary", "")[:140]
        website = l.get("website", "")
        cards += f"""
<article class="card" data-ind="{ind}" data-stage="{stage}" data-amt="{amt or 0}">
  <div class="card-top">
    <div>
      <h2 class="co-name">{company[:60]}</h2>
      <span class="ind-tag">{ind}</span>
    </div>
    <span class="stage-badge" style="background:{sc}22;color:{sc};border-color:{sc}44">{stage}</span>
  </div>
  <p class="summary">{summary}</p>
  <div class="card-foot">
    <span class="amt">💰 {amt_str}</span>
    <span class="date">📅 {date_str}</span>
    {"<a class='web-link' href='" + website + "' target='_blank' rel='noopener'>Visit →</a>" if website else ""}
  </div>
</article>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<meta name="description" content="Track {len(leads)} recently funded startups. Filter by industry, round stage (Seed, Series A, B, C), and funding amount. Real-time B2B sales intelligence."/>
<meta name="keywords" content="startup funding tracker, recently funded startups, series a startups, venture capital deals, b2b lead generation, startup intelligence"/>
<meta property="og:title" content="FundRadar — Real-Time Startup Funding Intelligence"/>
<meta property="og:description" content="Track {len(leads)} funded startups. Filter by stage, industry, and funding amount."/>
<meta property="og:type" content="website"/>
<title>FundRadar — Startup Funding &amp; B2B Intelligence</title>
<script type="application/ld+json">{json.dumps(schema)}</script>
<style>
:root{{--bg:#060a12;--bg2:#0d1420;--card:#111827;--border:#1e2d40;--fg:#e2eaf4;--fg2:#7a8fa6;--fg3:#3d5068;--accent:#38bdf8;--green:#34d399;color-scheme:dark}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:var(--bg);color:var(--fg);line-height:1.6}}
header{{background:linear-gradient(160deg,#05111e 0%,#060a12 70%);padding:52px 20px 40px;text-align:center;border-bottom:1px solid var(--border)}}
.live{{display:inline-flex;align-items:center;gap:6px;font-size:11px;color:var(--green);font-weight:600;letter-spacing:.6px;text-transform:uppercase;margin-bottom:14px}}
.dot{{width:7px;height:7px;background:var(--green);border-radius:50%;animation:blink 2s infinite}}
@keyframes blink{{0%,100%{{opacity:1}}50%{{opacity:.2}}}}
h1{{font-size:clamp(1.7rem,4vw,2.8rem);font-weight:700;color:#fff;margin-bottom:8px}}
h1 span{{color:var(--accent)}}
.sub{{color:var(--fg2);font-size:.95rem;max-width:480px;margin:0 auto 24px}}
.cta-bar{{background:rgba(56,189,248,.07);border:1px solid rgba(56,189,248,.18);border-radius:8px;padding:11px 16px;max-width:600px;margin:0 auto;font-size:13px;color:var(--fg2)}}
.cta-bar a{{color:var(--accent);font-weight:600}}
.stats{{display:flex;justify-content:center;background:var(--bg2);border-bottom:1px solid var(--border)}}
.stat{{text-align:center;padding:16px 24px;border-right:1px solid var(--border);flex:1;max-width:160px}}
.stat:last-child{{border-right:none}}
.sn{{font-size:1.4rem;font-weight:700;color:var(--accent)}}
.sl{{font-size:10px;color:var(--fg3);text-transform:uppercase;letter-spacing:.5px;margin-top:2px}}
.controls{{max-width:1040px;margin:24px auto;padding:0 16px;display:flex;flex-direction:column;gap:10px}}
.row{{display:flex;gap:8px;flex-wrap:wrap}}
#search{{flex:1;min-width:180px;background:var(--card);border:1px solid var(--border);border-radius:7px;padding:8px 12px;color:var(--fg);font-size:13px;outline:none}}
#search:focus{{border-color:var(--accent)}}
select{{background:var(--card);border:1px solid var(--border);border-radius:7px;padding:8px 12px;color:var(--fg);font-size:13px;cursor:pointer;outline:none}}
.filter-row{{display:flex;flex-wrap:wrap;gap:6px;align-items:center}}
.label{{font-size:11px;color:var(--fg3);margin-right:2px}}
.f-btn{{background:var(--bg2);border:1px solid var(--border);color:var(--fg2);padding:3px 10px;border-radius:20px;font-size:11px;cursor:pointer;transition:.12s}}
.f-btn:hover,.f-btn.active{{background:var(--accent);color:#fff;border-color:var(--accent)}}
.count{{font-size:12px;color:var(--fg3)}}
.grid{{max-width:1040px;margin:0 auto;padding:0 16px 56px;display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:13px}}
.card{{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:16px;display:flex;flex-direction:column;gap:10px;transition:border-color .15s}}
.card:hover{{border-color:var(--accent)}}
.card.hidden{{display:none}}
.card-top{{display:flex;justify-content:space-between;align-items:flex-start;gap:10px}}
.co-name{{font-size:13px;font-weight:600;color:var(--fg);margin-bottom:4px;line-height:1.3}}
.ind-tag{{font-size:10px;color:var(--fg3);background:var(--bg2);padding:2px 6px;border-radius:3px}}
.stage-badge{{font-size:10px;font-weight:700;padding:3px 8px;border-radius:4px;white-space:nowrap;flex-shrink:0;border:1px solid}}
.summary{{font-size:11px;color:var(--fg2);flex:1;line-height:1.5}}
.card-foot{{display:flex;gap:12px;align-items:center;flex-wrap:wrap}}
.amt{{font-size:12px;font-weight:600;color:var(--green)}}
.date{{font-size:11px;color:var(--fg3)}}
.web-link{{font-size:11px;color:var(--accent);text-decoration:none;margin-left:auto}}
.web-link:hover{{text-decoration:underline}}
.none{{display:none;text-align:center;padding:48px;color:var(--fg3)}}
.none.show{{display:block}}
footer{{text-align:center;padding:28px;border-top:1px solid var(--border);color:var(--fg3);font-size:12px}}
footer a{{color:var(--accent)}}
@media(max-width:560px){{.stats{{flex-wrap:wrap}}.stat{{min-width:50%;border-right:none;border-bottom:1px solid var(--border)}}}}
</style>
</head>
<body>
<header>
  <div class="live"><span class="dot"></span>Updated {updated}</div>
  <h1>Fund<span>Radar</span></h1>
  <p class="sub">Real-time startup funding intelligence. Track newly funded companies for B2B sales, recruiting, and investment research.</p>
  <div class="cta-bar">Need API access? <a href="{RAPIDAPI_URL}" target="_blank">Subscribe on RapidAPI</a> — filter by stage, industry, funding amount.</div>
</header>
<div class="stats">
  <div class="stat"><div class="sn">{len(leads)}</div><div class="sl">Companies</div></div>
  <div class="stat"><div class="sn">{len(funded)}</div><div class="sl">With Amount</div></div>
  <div class="stat"><div class="sn">{fmt_usd(total_vc) or "$0"}</div><div class="sl">Total Tracked</div></div>
  <div class="stat"><div class="sn">{len(industries)}</div><div class="sl">Industries</div></div>
</div>
<div class="controls">
  <div class="row">
    <input id="search" type="search" placeholder="Search company, industry, summary..." oninput="fil()"/>
    <select id="amt-sel" onchange="fil()">
      <option value="0">Any Amount</option>
      <option value="1000000">$1M+</option>
      <option value="5000000">$5M+</option>
      <option value="10000000">$10M+</option>
      <option value="50000000">$50M+</option>
    </select>
  </div>
  <div class="filter-row">
    <span class="label">Stage:</span>{stage_buttons}
  </div>
  <div class="filter-row">
    <span class="label">Industry:</span>{ind_buttons}
    <button class="f-btn" id="clear-btn" onclick="clearAll()" style="display:none">✕ Clear</button>
  </div>
  <div class="count" id="count">{len(leads)} companies shown</div>
</div>
<div class="grid" id="grid">{cards}</div>
<div class="none" id="none">No results. <a href="#" onclick="clearAll();return false">Clear filters</a></div>
<footer><a href="{RAPIDAPI_URL}" target="_blank">API on RapidAPI</a> · <a href="{GITHUB_URL}" target="_blank">GitHub</a> · Updated daily</footer>
<script>
let aInd=null,aStage=null;
function fil(){{
  const q=document.getElementById('search').value.toLowerCase();
  const minA=parseInt(document.getElementById('amt-sel').value)||0;
  let n=0;
  document.querySelectorAll('.card').forEach(c=>{{
    const ok=(!q||c.innerText.toLowerCase().includes(q))&&
              (parseInt(c.dataset.amt)>=minA)&&
              (!aInd||c.dataset.ind===aInd)&&
              (!aStage||c.dataset.stage===aStage);
    c.classList.toggle('hidden',!ok);
    if(ok)n++;
  }});
  document.getElementById('count').textContent=n+' companies shown';
  document.getElementById('none').classList.toggle('show',n===0);
  document.getElementById('clear-btn').style.display=(q||minA||aInd||aStage)?'inline-block':'none';
}}
function filterInd(v){{aInd=aInd===v?null:v;document.querySelectorAll('.f-btn').forEach(b=>b.classList.toggle('active',b.textContent===v&&aInd));fil();}}
function filterStage(v){{aStage=aStage===v?null:v;document.querySelectorAll('.f-btn').forEach(b=>b.classList.toggle('active',b.textContent===v&&aStage));fil();}}
function clearAll(){{aInd=null;aStage=null;document.getElementById('search').value='';document.getElementById('amt-sel').value='0';document.querySelectorAll('.f-btn').forEach(b=>b.classList.remove('active'));fil();}}
</script>
</body></html>"""


def main():
    print("Loading leads...")
    leads = load_leads()
    print(f"Loaded {len(leads)} leads.")
    DIST_DIR.mkdir(exist_ok=True)
    print("Building index.html...")
    (DIST_DIR / "index.html").write_text(build_index(leads), encoding="utf-8")
    (DIST_DIR / "robots.txt").write_text(
        "User-agent: *\nAllow: /\nSitemap: https://nxtcraft.github.io/fundradar/sitemap.xml\n"
    )
    (DIST_DIR / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f'  <url><loc>https://nxtcraft.github.io/fundradar/</loc><lastmod>{datetime.now(timezone.utc).strftime("%Y-%m-%d")}</lastmod><changefreq>daily</changefreq><priority>1.0</priority></url>\n'
        "</urlset>\n"
    )
    (DIST_DIR / "404.html").write_text(
        '<!DOCTYPE html><html><head><meta charset="UTF-8"/><title>Not Found – FundRadar</title>'
        '<style>body{font-family:sans-serif;background:#060a12;color:#e2eaf4;display:flex;align-items:center;justify-content:center;height:100vh;text-align:center}</style></head>'
        '<body><div><h1 style="color:#38bdf8;font-size:3rem">404</h1><p style="color:#7a8fa6;margin:12px 0 24px">Page not found.</p>'
        '<a href="/fundradar/" style="background:#38bdf8;color:#fff;padding:10px 22px;border-radius:7px;text-decoration:none;font-weight:600">Back to FundRadar →</a></div></body></html>',
        encoding="utf-8",
    )
    print(f"Done. {len(list(DIST_DIR.iterdir()))} files in dist/")


if __name__ == "__main__":
    main()
