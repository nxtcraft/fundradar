"""
Startup Funding & B2B Lead Intelligence API
FastAPI microservice serving normalized startup funding data.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

DATA_FILE = Path("data/latest_funding.json")

app = FastAPI(
    title="Startup Funding & B2B Lead Intelligence API",
    description=(
        "Track newly funded startups with normalized round sizes, stages, "
        "tech categories, and founder websites. Ideal for B2B sales teams, "
        "recruiters, and venture intelligence workflows."
    ),
    version="1.0.0",
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
    data_file: str
    timestamp: str


class StatsResponse(BaseModel):
    total_vc_tracked_usd: int
    by_industry: dict[str, int]
    by_round_type: dict[str, int]
    total_companies: int


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


# ──────────────────────────────────────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["Meta"])
def health():
    leads = _load_leads()
    return {
        "status": "ok",
        "total_companies": len(leads),
        "data_file": str(DATA_FILE),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/v1/leads", response_model=list[FundingLead], tags=["Leads"])
def list_leads(
    stage: Optional[str] = Query(None, description="Filter by round type (e.g. Seed, Series A)"),
    industry: Optional[str] = Query(None, description="Filter by industry (e.g. AI/ML, Fintech)"),
    min_funding_usd: Optional[int] = Query(None, description="Minimum funding amount in USD"),
    limit: int = Query(25, ge=1, le=100, description="Max results to return (1–100)"),
):
    leads = _load_leads()
    if not leads:
        raise HTTPException(status_code=503, detail="No funding data available. Run pipeline.py to ingest.")

    # Apply filters
    if stage:
        leads = [l for l in leads if l.get("round_type", "").lower() == stage.lower()]
    if industry:
        leads = [l for l in leads if industry.lower() in l.get("industry", "").lower()]
    if min_funding_usd is not None:
        leads = [l for l in leads if (l.get("amount_usd") or 0) >= min_funding_usd]

    # Sort by announced_date descending (already sorted in pipeline, but enforce here)
    leads.sort(key=lambda x: x.get("announced_date", ""), reverse=True)

    return leads[:limit]


@app.get("/v1/stats", response_model=StatsResponse, tags=["Analytics"])
def stats():
    leads = _load_leads()
    if not leads:
        raise HTTPException(status_code=503, detail="No funding data available. Run pipeline.py to ingest.")

    total_vc = sum(l.get("amount_usd") or 0 for l in leads)

    by_industry: dict[str, int] = {}
    for l in leads:
        ind = l.get("industry", "Other")
        by_industry[ind] = by_industry.get(ind, 0) + 1

    by_round: dict[str, int] = {}
    for l in leads:
        rt = l.get("round_type", "Unknown")
        by_round[rt] = by_round.get(rt, 0) + 1

    return {
        "total_vc_tracked_usd": total_vc,
        "by_industry": by_industry,
        "by_round_type": by_round,
        "total_companies": len(leads),
    }
