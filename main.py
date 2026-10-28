"""
Startup Funding & B2B Lead Intelligence API
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

DATA_FILE = Path("data/latest_funding.json")
templates = Jinja2Templates(directory="templates")

app = FastAPI(
    title="Startup Funding & B2B Lead Intelligence API",
    description=(
        "Track newly funded startups with normalized round sizes, stages, "
        "tech categories, and websites. Updated daily. Ideal for B2B sales "
        "teams, recruiters, and venture intelligence workflows."
    ),
    version="1.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────────────────────────────────────
# Models
# ──────────────────────────────────────────────────────────────────────────────

class FundingLead(BaseModel):
    id: str
    company_name: str
    website: str
    round_type: str
    amount_usd: Optional[int]
    industry: str
    summary: str
    announced_date: str
    ingested_at: str


class HealthResponse(BaseModel):
    status: str
    total_companies: int
    last_ingested: Optional[str]
    timestamp: str


class StatsResponse(BaseModel):
    total_vc_tracked_usd: int
    total_vc_tracked_formatted: str
    by_industry: dict[str, int]
    by_round_type: dict[str, int]
    total_companies: int


class LeadsResponse(BaseModel):
    total: int
    offset: int
    limit: int
    results: list[FundingLead]


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _load_leads() -> list[dict]:
    if not DATA_FILE.exists():
        return []
    try:
        return json.loads(DATA_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return []


def _fmt_usd(amount: int) -> str:
    if amount >= 1_000_000_000:
        return f"${amount / 1_000_000_000:.1f}B"
    if amount >= 1_000_000:
        return f"${amount / 1_000_000:.0f}M"
    if amount >= 1_000:
        return f"${amount / 1_000:.0f}K"
    return f"${amount}"


# ──────────────────────────────────────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────────────────────────────────────

_IND_CLASS = {
    "AI/ML": "ind-aiml", "Fintech": "ind-fintech", "DevTools": "ind-devtools",
    "HealthTech": "ind-health", "B2B SaaS": "ind-saas", "Security": "ind-security",
    "CleanTech": "ind-clean", "EdTech": "ind-edtech", "HR Tech": "ind-hr",
    "E-commerce": "ind-ecomm",
}
_STAGE_CLASS = {
    "Pre-Seed": "stage-preseed", "Seed": "stage-seed", "Series A": "stage-seriesa",
    "Series B": "stage-seriesb", "Series C": "stage-seriesc", "Series D": "stage-seriesd",
    "Growth": "stage-growth",
}


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def homepage(request: Request):
    leads = _load_leads()
    total_vc_raw = sum(l.get("amount_usd") or 0 for l in leads)
    industries = len({l.get("industry") for l in leads if l.get("industry")})

    enriched = []
    for l in leads:
        amt = l.get("amount_usd")
        raw_date = l.get("announced_date", "")
        try:
            from datetime import date
            d = date.fromisoformat(raw_date)
            date_fmt = d.strftime("%b %Y")
        except Exception:
            date_fmt = raw_date
        enriched.append({
            **l,
            "amount_fmt": _fmt_usd(amt) if amt else None,
            "ind_cls": _IND_CLASS.get(l.get("industry", ""), "ind-other"),
            "stage_cls": _STAGE_CLASS.get(l.get("round_type", ""), "stage-seed"),
            "date_fmt": date_fmt,
        })

    return templates.TemplateResponse(request, "index.html", {
        "leads": enriched,
        "total": len(leads),
        "total_vc": _fmt_usd(total_vc_raw) if total_vc_raw else "$0",
        "industries": industries,
    })


@app.get("/robots.txt", include_in_schema=False)
def robots():
    return Response(
        content="User-agent: *\nAllow: /\nSitemap: https://fundradar-xx7t.onrender.com/sitemap.xml\n",
        media_type="text/plain",
    )


@app.get("/sitemap.xml", include_in_schema=False)
def sitemap():
    leads = _load_leads()
    urls = ["https://fundradar-xx7t.onrender.com/"]
    for lead in leads:
        if lead.get("website"):
            pass  # external sites not included
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for url in urls:
        xml += f"  <url><loc>{url}</loc><changefreq>daily</changefreq><priority>1.0</priority></url>\n"
    xml += "</urlset>"
    return Response(content=xml, media_type="application/xml")


@app.get("/health", response_model=HealthResponse, tags=["Meta"])
def health():
    leads = _load_leads()
    last_ingested = leads[0].get("ingested_at") if leads else None
    return {
        "status": "ok",
        "total_companies": len(leads),
        "last_ingested": last_ingested,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/v1/leads", response_model=LeadsResponse, tags=["Leads"])
def list_leads(
    response: Response,
    stage: Optional[str] = Query(None, description="Filter by round type (Seed, Series A, Series B, Series C, Growth)"),
    industry: Optional[str] = Query(None, description="Filter by industry (AI/ML, Fintech, DevTools, HealthTech, B2B SaaS, Security, CleanTech, EdTech, HR Tech, E-commerce)"),
    min_funding_usd: Optional[int] = Query(None, description="Minimum funding in USD (e.g. 1000000)"),
    max_funding_usd: Optional[int] = Query(None, description="Maximum funding in USD"),
    search: Optional[str] = Query(None, description="Free-text search across company name and summary"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(25, ge=1, le=100, description="Results per page (max 100)"),
):
    leads = _load_leads()
    if not leads:
        raise HTTPException(status_code=503, detail="No funding data available. Run pipeline.py to ingest.")

    if stage:
        leads = [l for l in leads if l.get("round_type", "").lower() == stage.lower()]
    if industry:
        leads = [l for l in leads if industry.lower() in l.get("industry", "").lower()]
    if min_funding_usd is not None:
        leads = [l for l in leads if (l.get("amount_usd") or 0) >= min_funding_usd]
    if max_funding_usd is not None:
        leads = [l for l in leads if (l.get("amount_usd") or 0) <= max_funding_usd]
    if search:
        q = search.lower()
        leads = [
            l for l in leads
            if q in l.get("company_name", "").lower() or q in l.get("summary", "").lower()
        ]

    leads.sort(key=lambda x: x.get("announced_date", ""), reverse=True)

    total = len(leads)
    page = leads[offset: offset + limit]

    response.headers["X-Total-Count"] = str(total)
    return {"total": total, "offset": offset, "limit": limit, "results": page}


@app.get("/v1/company/{company_id}", response_model=FundingLead, tags=["Leads"])
def get_company(company_id: str):
    leads = _load_leads()
    for lead in leads:
        if lead.get("id") == company_id:
            return lead
    raise HTTPException(status_code=404, detail=f"Company '{company_id}' not found.")


@app.get("/v1/stats", response_model=StatsResponse, tags=["Analytics"])
def stats():
    leads = _load_leads()
    if not leads:
        raise HTTPException(status_code=503, detail="No funding data available. Run pipeline.py to ingest.")

    total_vc = sum(l.get("amount_usd") or 0 for l in leads)

    by_industry: dict[str, int] = {}
    for l in leads:
        k = l.get("industry", "Other")
        by_industry[k] = by_industry.get(k, 0) + 1

    by_round: dict[str, int] = {}
    for l in leads:
        k = l.get("round_type", "Unknown")
        by_round[k] = by_round.get(k, 0) + 1

    return {
        "total_vc_tracked_usd": total_vc,
        "total_vc_tracked_formatted": _fmt_usd(total_vc),
        "by_industry": dict(sorted(by_industry.items(), key=lambda x: -x[1])),
        "by_round_type": dict(sorted(by_round.items(), key=lambda x: -x[1])),
        "total_companies": len(leads),
    }
