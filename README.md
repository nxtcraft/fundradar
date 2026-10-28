# fundradar 🎯

**Startup Funding & B2B Lead Intelligence API**

Track newly funded startups with normalized round sizes, stages, tech categories, and websites. Updated daily via GitHub Actions. Built for B2B sales teams, recruiters, and venture intelligence workflows.

---

## Live API

```
GET /health                  → operational status
GET /v1/leads                → paginated funding leads with filters
GET /v1/company/{id}         → single company lookup
GET /v1/stats                → VC totals, breakdown by industry & stage
GET /docs                    → interactive Swagger UI
```

---

## Endpoints

### `GET /v1/leads`

| Parameter | Type | Description |
|---|---|---|
| `stage` | string | Seed, Series A, Series B, Series C, Growth |
| `industry` | string | AI/ML, Fintech, DevTools, HealthTech, B2B SaaS, Security, CleanTech, EdTech, HR Tech |
| `min_funding_usd` | int | Minimum round size in USD |
| `max_funding_usd` | int | Maximum round size in USD |
| `search` | string | Full-text search on company name + summary |
| `offset` | int | Pagination offset (default 0) |
| `limit` | int | Results per page, max 100 (default 25) |

**Response includes `X-Total-Count` header** with total matching records.

**Example:**
```bash
curl "https://your-api.onrender.com/v1/leads?stage=Series+A&industry=AI%2FML&limit=10"
```

```json
{
  "total": 4,
  "offset": 0,
  "limit": 10,
  "results": [
    {
      "id": "sakana-ai-series-a",
      "company_name": "Sakana AI",
      "website": "https://sakana.ai",
      "round_type": "Series A",
      "amount_usd": 214000000,
      "industry": "AI/ML",
      "summary": "Tokyo-based AI lab applying nature-inspired intelligence to model design.",
      "announced_date": "2024-08-07",
      "ingested_at": "2025-01-01T06:00:00+00:00"
    }
  ]
}
```

### `GET /v1/stats`

```json
{
  "total_vc_tracked_usd": 28500000000,
  "total_vc_tracked_formatted": "$28B",
  "by_industry": { "AI/ML": 11, "DevTools": 5, "Fintech": 4 },
  "by_round_type": { "Series B": 8, "Growth": 5, "Seed": 4 }
}
```

---

## Run Locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python pipeline.py          # seed data/latest_funding.json
uvicorn main:app --reload   # → http://localhost:8000/docs
```

## Run Tests

```bash
pytest test_pipeline.py -v
```

## Deploy to Render

1. Push repo to GitHub
2. Go to [render.com](https://render.com) → New → Web Service
3. Connect `fundradar` repo — `render.yaml` handles the rest
4. Your API is live at `https://fundradar.onrender.com`

## Data Pipeline

The `pipeline.py` ingests from:
- **YC API** — W25 + S24 batch companies
- **Hacker News** — "Show HN" posts mentioning fundraising
- **Curated seed dataset** — 38 verified 2022–2025 funding rounds

GitHub Actions runs `pipeline.py` daily at 06:00 UTC and auto-commits `data/latest_funding.json`.

---

## Monetisation

List on [RapidAPI](https://rapidapi.com) with tiers:
- **Free** — 100 req/day, Seed rounds only
- **Pro** ($49/mo) — 5,000 req/day, all stages + filters
- **Business** ($199/mo) — unlimited, bulk export, webhook alerts

---

*Built with FastAPI · Deployed on Render · Data refreshed daily*
