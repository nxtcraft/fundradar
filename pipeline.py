"""
Startup Funding & Lead Intelligence ingestion pipeline.

Fetches recent funding announcements from public sources (YC launches API,
Hacker News "Show HN" funding posts) and writes normalized JSON to
data/latest_funding.json.
"""

import asyncio
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx

DATA_FILE = Path("data/latest_funding.json")

# ──────────────────────────────────────────────────────────────────────────────
# Amount normalisation
# ──────────────────────────────────────────────────────────────────────────────

_MULTIPLIERS = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}

# Rough USD → EUR / GBP conversion factors (good-enough for aggregation)
_CURRENCY_TO_USD = {"$": 1.0, "€": 1.08, "£": 1.27}


def parse_funding_amount(raw: str) -> Optional[int]:
    """Convert human-readable funding strings to integer USD amounts.

    Examples
    --------
    "$4.5M"  → 4_500_000
    "$750K"  → 750_000
    "€3M"    → 3_240_000
    "Undisclosed" | "" | None → None
    """
    if not raw:
        return None
    text = raw.strip()
    # Match optional currency symbol, numeric value, optional suffix K/M/B
    m = re.search(r"([$€£]?)\s*([\d,]+(?:\.\d+)?)\s*([KMBkmb]?)", text)
    if not m:
        return None
    currency_sym, number_str, suffix = m.group(1), m.group(2), m.group(3).upper()
    try:
        amount = float(number_str.replace(",", ""))
    except ValueError:
        return None
    if suffix in _MULTIPLIERS:
        amount *= _MULTIPLIERS[suffix]
    usd_rate = _CURRENCY_TO_USD.get(currency_sym, 1.0)
    return int(amount * usd_rate)


# ──────────────────────────────────────────────────────────────────────────────
# Industry classification (keyword-based)
# ──────────────────────────────────────────────────────────────────────────────

_INDUSTRY_KEYWORDS: list[tuple[str, list[str]]] = [
    ("AI/ML", ["ai", "machine learning", "llm", "gpt", "generative", "neural", "nlp", "ml"]),
    ("Fintech", ["fintech", "payment", "banking", "crypto", "defi", "lending", "insurance"]),
    ("DevTools", ["devtools", "developer", "sdk", "api", "cli", "infrastructure", "platform", "open source"]),
    ("HealthTech", ["health", "medical", "biotech", "clinical", "pharma", "wellness", "mental"]),
    ("B2B SaaS", ["saas", "b2b", "enterprise", "crm", "erp", "workflow", "automation", "productivity"]),
    ("CleanTech", ["climate", "carbon", "energy", "solar", "ev", "sustainable", "green"]),
    ("E-commerce", ["ecommerce", "e-commerce", "retail", "marketplace", "commerce"]),
]


def classify_industry(text: str) -> str:
    lower = text.lower()
    for industry, keywords in _INDUSTRY_KEYWORDS:
        if any(kw in lower for kw in keywords):
            return industry
    return "Other"


# ──────────────────────────────────────────────────────────────────────────────
# Round type classification
# ──────────────────────────────────────────────────────────────────────────────

def classify_round(text: str, amount_usd: Optional[int]) -> str:
    lower = text.lower()
    for stage in ("series c", "series b", "series a", "seed", "pre-seed", "growth"):
        if stage in lower:
            return stage.title().replace("-S", "-s")
    # Infer from amount if stage not named
    if amount_usd is None:
        return "Seed"
    if amount_usd >= 50_000_000:
        return "Series B"
    if amount_usd >= 10_000_000:
        return "Series A"
    if amount_usd >= 1_000_000:
        return "Seed"
    return "Pre-Seed"


# ──────────────────────────────────────────────────────────────────────────────
# YC launches feed (public JSON API)
# ──────────────────────────────────────────────────────────────────────────────

YC_LAUNCHES_URL = "https://api.ycombinator.com/v0.1/companies?batch=W25&limit=50"
HN_LAUNCHES_URL = "https://hacker-news.firebaseio.com/v0/newstories.json"
HN_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{id}.json"

# Fallback seed dataset so the engine always has data even if all feeds fail
SEED_DATA: list[dict] = [
    {
        "id": "openai-2023",
        "company_name": "OpenAI",
        "website": "https://openai.com",
        "round_type": "Growth",
        "amount_usd": 10_000_000_000,
        "industry": "AI/ML",
        "summary": "Builds general-purpose AI systems including GPT-4 and DALL-E.",
        "announced_date": "2023-01-23",
    },
    {
        "id": "mistral-seed",
        "company_name": "Mistral AI",
        "website": "https://mistral.ai",
        "round_type": "Seed",
        "amount_usd": 113_000_000,
        "industry": "AI/ML",
        "summary": "Develops efficient open-weight large language models.",
        "announced_date": "2023-06-13",
    },
    {
        "id": "anysphere-series-a",
        "company_name": "Anysphere (Cursor)",
        "website": "https://cursor.sh",
        "round_type": "Series A",
        "amount_usd": 60_000_000,
        "industry": "DevTools",
        "summary": "AI-powered code editor built on VS Code for developer productivity.",
        "announced_date": "2024-01-11",
    },
    {
        "id": "perplexity-series-b",
        "company_name": "Perplexity AI",
        "website": "https://perplexity.ai",
        "round_type": "Series B",
        "amount_usd": 73_600_000,
        "industry": "AI/ML",
        "summary": "Conversational AI search engine with cited, real-time answers.",
        "announced_date": "2024-01-04",
    },
    {
        "id": "harvey-series-b",
        "company_name": "Harvey AI",
        "website": "https://harvey.ai",
        "round_type": "Series B",
        "amount_usd": 80_000_000,
        "industry": "B2B SaaS",
        "summary": "AI legal assistant for law firms and corporate counsel teams.",
        "announced_date": "2024-02-07",
    },
    {
        "id": "cohere-series-c",
        "company_name": "Cohere",
        "website": "https://cohere.com",
        "round_type": "Series C",
        "amount_usd": 270_000_000,
        "industry": "AI/ML",
        "summary": "Enterprise NLP platform for building search and generation pipelines.",
        "announced_date": "2023-06-08",
    },
    {
        "id": "baseten-series-b",
        "company_name": "Baseten",
        "website": "https://baseten.co",
        "round_type": "Series B",
        "amount_usd": 40_000_000,
        "industry": "DevTools",
        "summary": "ML model deployment infrastructure for production inference.",
        "announced_date": "2023-10-03",
    },
    {
        "id": "brex-growth",
        "company_name": "Brex",
        "website": "https://brex.com",
        "round_type": "Growth",
        "amount_usd": 300_000_000,
        "industry": "Fintech",
        "summary": "Corporate cards and spend management for startups and enterprises.",
        "announced_date": "2022-10-19",
    },
    {
        "id": "rippling-series-f",
        "company_name": "Rippling",
        "website": "https://rippling.com",
        "round_type": "Series B",
        "amount_usd": 500_000_000,
        "industry": "B2B SaaS",
        "summary": "Unified workforce management platform covering HR, IT, and Finance.",
        "announced_date": "2023-03-14",
    },
    {
        "id": "carbon-health-series-c",
        "company_name": "Carbon Health",
        "website": "https://carbonhealth.com",
        "round_type": "Series C",
        "amount_usd": 100_000_000,
        "industry": "HealthTech",
        "summary": "Tech-enabled primary care clinics with integrated digital health tools.",
        "announced_date": "2022-04-26",
    },
]


async def fetch_yc_companies(client: httpx.AsyncClient) -> list[dict]:
    """Fetch latest YC W25 batch companies."""
    try:
        resp = await client.get(YC_LAUNCHES_URL, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        companies = data.get("companies", [])
        results = []
        now = datetime.now(timezone.utc).date().isoformat()
        for c in companies[:30]:
            name = c.get("name", "").strip()
            if not name:
                continue
            website = c.get("website") or c.get("url") or ""
            description = c.get("one_liner") or c.get("long_description") or ""
            slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
            results.append({
                "id": f"yc-{slug}",
                "company_name": name,
                "website": website,
                "round_type": "Seed",
                "amount_usd": 500_000,  # Standard YC deal
                "industry": classify_industry(description),
                "summary": description[:200] if description else f"{name} — YC W25 batch company.",
                "announced_date": now,
            })
        return results
    except Exception:
        return []


async def fetch_hn_show_launches(client: httpx.AsyncClient, max_items: int = 20) -> list[dict]:
    """Scan recent HN items for 'Show HN: We raised' style posts."""
    try:
        resp = await client.get(HN_LAUNCHES_URL, timeout=10)
        story_ids = resp.json()[:200]
    except Exception:
        return []

    results = []
    tasks = [client.get(HN_ITEM_URL.format(id=sid), timeout=8) for sid in story_ids]
    responses = await asyncio.gather(*tasks, return_exceptions=True)

    funding_pattern = re.compile(
        r"raised?\s+([$€£][\d,.]+[KMBkmb]?)", re.IGNORECASE
    )

    for r in responses:
        if isinstance(r, Exception) or r.status_code != 200:
            continue
        try:
            item = r.json()
        except Exception:
            continue
        title = item.get("title", "")
        text = item.get("text", "") or ""
        url = item.get("url", "")
        # Only Show HN posts that mention fundraising
        if not title.lower().startswith("show hn"):
            continue
        combined = f"{title} {text}"
        m = funding_pattern.search(combined)
        if not m:
            continue
        raw_amount = m.group(1)
        amount_usd = parse_funding_amount(raw_amount)
        name = re.sub(r"^show hn:\s*", "", title, flags=re.IGNORECASE).split("–")[0].split("-")[0].strip()
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        ts = item.get("time", 0)
        announced = datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat() if ts else datetime.now(timezone.utc).date().isoformat()
        results.append({
            "id": f"hn-{slug}-{item.get('id', '')}",
            "company_name": name[:80],
            "website": url,
            "round_type": classify_round(combined, amount_usd),
            "amount_usd": amount_usd,
            "industry": classify_industry(combined),
            "summary": title[:200],
            "announced_date": announced,
        })
        if len(results) >= max_items:
            break
    return results


# ──────────────────────────────────────────────────────────────────────────────
# Main pipeline entry point
# ──────────────────────────────────────────────────────────────────────────────

async def run_pipeline() -> list[dict]:
    now_utc = datetime.now(timezone.utc).isoformat()
    async with httpx.AsyncClient(follow_redirects=True) as client:
        yc, hn = await asyncio.gather(
            fetch_yc_companies(client),
            fetch_hn_show_launches(client),
        )

    # Merge live + seed, deduplicate by id
    live = yc + hn
    seen: set[str] = set()
    merged: list[dict] = []
    for item in live:
        if item["id"] not in seen:
            seen.add(item["id"])
            merged.append(item)

    for seed in SEED_DATA:
        if seed["id"] not in seen:
            seen.add(seed["id"])
            merged.append(seed)

    # Sort by announced_date descending
    merged.sort(key=lambda x: x.get("announced_date", ""), reverse=True)

    # Stamp ingestion time
    output = [
        {**entry, "ingested_at": now_utc}
        for entry in merged
    ]

    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(output, indent=2))
    print(f"[pipeline] Wrote {len(output)} records → {DATA_FILE}")
    return output


if __name__ == "__main__":
    asyncio.run(run_pipeline())
