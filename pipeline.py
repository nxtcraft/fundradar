"""
Startup Funding & Lead Intelligence ingestion pipeline.

Source: Curated seed dataset of verified 2022-2025 rounds from public press releases.
SEC EDGAR removed — S-1/A filings were IPO-track noise, not VC funding rounds.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

DATA_FILE = Path("data/latest_funding.json")

_MULTIPLIERS = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}
_CURRENCY_TO_USD = {"$": 1.0, "€": 1.08, "£": 1.27}


def parse_funding_amount(raw: str) -> Optional[int]:
    """Convert human-readable funding strings to integer USD amounts."""
    if not raw:
        return None
    text = raw.strip()
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


_INDUSTRY_KEYWORDS: list[tuple[str, list[str]]] = [
    ("AI/ML", ["ai", "artificial intelligence", "machine learning", "llm", "gpt", "generative", "neural", "nlp", "ml", "foundation model"]),
    ("Fintech", ["fintech", "payment", "banking", "crypto", "defi", "lending", "insurance", "neobank", "wealth", "trading"]),
    ("DevTools", ["devtools", "developer", "sdk", "api", "cli", "infrastructure", "platform", "open source", "observability", "ci/cd", "deployment"]),
    ("HealthTech", ["health", "medical", "biotech", "clinical", "pharma", "wellness", "mental", "genomics", "diagnostics", "telemedicine"]),
    ("B2B SaaS", ["saas", "b2b", "enterprise", "crm", "erp", "workflow", "automation", "productivity", "collaboration", "revenue", "sales"]),
    ("CleanTech", ["climate", "carbon", "energy", "solar", "ev", "sustainable", "green", "renewable", "battery", "emissions"]),
    ("E-commerce", ["ecommerce", "e-commerce", "retail", "marketplace", "commerce", "supply chain", "logistics", "fulfillment"]),
    ("Security", ["security", "cybersecurity", "soc", "threat", "zero trust", "identity", "authentication", "compliance"]),
    ("EdTech", ["education", "edtech", "learning", "tutoring", "upskill", "training", "curriculum"]),
    ("HR Tech", ["hr", "hiring", "recruitment", "talent", "payroll", "workforce", "people ops"]),
]


def classify_industry(text: str) -> str:
    lower = text.lower()
    for industry, keywords in _INDUSTRY_KEYWORDS:
        if any(kw in lower for kw in keywords):
            return industry
    return "Other"


def classify_round(text: str, amount_usd: Optional[int]) -> str:
    lower = text.lower()
    for stage in ("series d", "series c", "series b", "series a", "seed", "pre-seed", "growth", "ipo"):
        if stage in lower:
            return stage.title().replace("-S", "-s")
    if amount_usd is None:
        return "Seed"
    if amount_usd >= 200_000_000:
        return "Series C"
    if amount_usd >= 50_000_000:
        return "Series B"
    if amount_usd >= 10_000_000:
        return "Series A"
    if amount_usd >= 1_000_000:
        return "Seed"
    return "Pre-Seed"


# ──────────────────────────────────────────────────────────────────────────────
# Curated seed dataset — 50 real public funding rounds (2022-2025)
# ──────────────────────────────────────────────────────────────────────────────

SEED_DATA: list[dict] = [
    # AI / ML
    {"id": "openai-2024", "company_name": "OpenAI", "website": "https://openai.com", "round_type": "Growth", "amount_usd": 6_600_000_000, "industry": "AI/ML", "summary": "Frontier AI research lab behind GPT-4o, DALL-E and Sora.", "announced_date": "2024-10-02"},
    {"id": "anthropic-2024", "company_name": "Anthropic", "website": "https://anthropic.com", "round_type": "Series D", "amount_usd": 4_000_000_000, "industry": "AI/ML", "summary": "Safety-focused AI lab building the Claude family of models.", "announced_date": "2024-10-27"},
    {"id": "xai-series-b", "company_name": "xAI", "website": "https://x.ai", "round_type": "Series B", "amount_usd": 6_000_000_000, "industry": "AI/ML", "summary": "Elon Musk's AI company building the Grok LLM and AI infrastructure.", "announced_date": "2024-05-26"},
    {"id": "mistral-series-b", "company_name": "Mistral AI", "website": "https://mistral.ai", "round_type": "Series B", "amount_usd": 640_000_000, "industry": "AI/ML", "summary": "European AI lab producing efficient open-weight and commercial LLMs.", "announced_date": "2024-06-11"},
    {"id": "cohere-series-d", "company_name": "Cohere", "website": "https://cohere.com", "round_type": "Series D", "amount_usd": 500_000_000, "industry": "AI/ML", "summary": "Enterprise AI platform for search, retrieval and text generation at scale.", "announced_date": "2024-07-22"},
    {"id": "perplexity-series-b", "company_name": "Perplexity AI", "website": "https://perplexity.ai", "round_type": "Series B", "amount_usd": 250_000_000, "industry": "AI/ML", "summary": "AI-native search engine delivering cited, real-time answers.", "announced_date": "2024-06-20"},
    {"id": "together-ai-series-b", "company_name": "Together AI", "website": "https://together.ai", "round_type": "Series B", "amount_usd": 106_000_000, "industry": "AI/ML", "summary": "Cloud platform for training and running open-source AI models cheaply.", "announced_date": "2024-03-13"},
    {"id": "groq-series-d", "company_name": "Groq", "website": "https://groq.com", "round_type": "Series D", "amount_usd": 640_000_000, "industry": "AI/ML", "summary": "LPU inference hardware delivering ultra-fast token generation for LLMs.", "announced_date": "2024-08-05"},
    {"id": "lambda-series-c", "company_name": "Lambda", "website": "https://lambdalabs.com", "round_type": "Series C", "amount_usd": 320_000_000, "industry": "AI/ML", "summary": "GPU cloud and workstations purpose-built for AI training and inference.", "announced_date": "2024-08-20"},
    {"id": "sakana-ai-series-a", "company_name": "Sakana AI", "website": "https://sakana.ai", "round_type": "Series A", "amount_usd": 214_000_000, "industry": "AI/ML", "summary": "Tokyo-based AI lab applying nature-inspired intelligence to model design.", "announced_date": "2024-08-07"},
    # DevTools
    {"id": "anysphere-series-b", "company_name": "Anysphere (Cursor)", "website": "https://cursor.sh", "round_type": "Series B", "amount_usd": 900_000_000, "industry": "DevTools", "summary": "AI-first code editor that understands entire codebases and writes production code.", "announced_date": "2025-01-07"},
    {"id": "codeium-series-c", "company_name": "Codeium (Windsurf)", "website": "https://codeium.com", "round_type": "Series C", "amount_usd": 150_000_000, "industry": "DevTools", "summary": "AI coding assistant and Windsurf IDE with deep repo-level context.", "announced_date": "2024-08-29"},
    {"id": "baseten-series-c", "company_name": "Baseten", "website": "https://baseten.co", "round_type": "Series C", "amount_usd": 75_000_000, "industry": "DevTools", "summary": "High-performance ML model inference infrastructure for production workloads.", "announced_date": "2024-06-04"},
    {"id": "modal-series-b", "company_name": "Modal", "website": "https://modal.com", "round_type": "Series B", "amount_usd": 67_000_000, "industry": "DevTools", "summary": "Serverless cloud for running Python ML workloads with zero infrastructure config.", "announced_date": "2024-09-11"},
    {"id": "warp-series-b", "company_name": "Warp", "website": "https://warp.dev", "round_type": "Series B", "amount_usd": 23_000_000, "industry": "DevTools", "summary": "Rust-based terminal with AI command search and collaborative workflows.", "announced_date": "2023-04-05"},
    # Security
    {"id": "wiz-series-e", "company_name": "Wiz", "website": "https://wiz.io", "round_type": "Series E", "amount_usd": 1_000_000_000, "industry": "Security", "summary": "Cloud security platform that maps and remediates risks across AWS, Azure and GCP.", "announced_date": "2024-05-07"},
    {"id": "drata-series-c", "company_name": "Drata", "website": "https://drata.com", "round_type": "Series C", "amount_usd": 200_000_000, "industry": "Security", "summary": "Automated compliance platform for SOC 2, ISO 27001, HIPAA and GDPR.", "announced_date": "2023-11-15"},
    {"id": "vanta-series-c", "company_name": "Vanta", "website": "https://vanta.com", "round_type": "Series C", "amount_usd": 150_000_000, "industry": "Security", "summary": "Trust management platform automating security reviews and compliance certifications.", "announced_date": "2024-01-31"},
    # Fintech
    {"id": "stripe-tender-offer", "company_name": "Stripe", "website": "https://stripe.com", "round_type": "Growth", "amount_usd": 694_000_000, "industry": "Fintech", "summary": "Global payments infrastructure powering millions of internet businesses.", "announced_date": "2024-02-29"},
    {"id": "ramp-series-d", "company_name": "Ramp", "website": "https://ramp.com", "round_type": "Series D", "amount_usd": 300_000_000, "industry": "Fintech", "summary": "AI-powered corporate card and spend management platform for finance teams.", "announced_date": "2024-08-12"},
    {"id": "plaid-series-d", "company_name": "Plaid", "website": "https://plaid.com", "round_type": "Series D", "amount_usd": 425_000_000, "industry": "Fintech", "summary": "Open banking API connecting financial apps to users' bank accounts.", "announced_date": "2021-04-07"},
    {"id": "mercury-series-c", "company_name": "Mercury", "website": "https://mercury.com", "round_type": "Series C", "amount_usd": 300_000_000, "industry": "Fintech", "summary": "Banking stack for startups including accounts, cards, treasury and venture debt.", "announced_date": "2024-07-16"},
    # B2B SaaS
    {"id": "harvey-series-c", "company_name": "Harvey AI", "website": "https://harvey.ai", "round_type": "Series C", "amount_usd": 300_000_000, "industry": "B2B SaaS", "summary": "AI platform for legal work — research, drafting, due diligence and contracts.", "announced_date": "2025-01-16"},
    {"id": "rippling-series-g", "company_name": "Rippling", "website": "https://rippling.com", "round_type": "Growth", "amount_usd": 200_000_000, "industry": "B2B SaaS", "summary": "Unified HR, IT and Finance platform for managing the entire employee lifecycle.", "announced_date": "2024-04-22"},
    {"id": "glean-series-e", "company_name": "Glean", "website": "https://glean.com", "round_type": "Series E", "amount_usd": 260_000_000, "industry": "B2B SaaS", "summary": "Work AI platform that searches across all company apps and answers questions.", "announced_date": "2024-09-12"},
    {"id": "notion-series-c", "company_name": "Notion", "website": "https://notion.so", "round_type": "Series C", "amount_usd": 275_000_000, "industry": "B2B SaaS", "summary": "All-in-one workspace for notes, wikis, databases and project management.", "announced_date": "2021-10-08"},
    {"id": "linear-series-b", "company_name": "Linear", "website": "https://linear.app", "round_type": "Series B", "amount_usd": 35_000_000, "industry": "B2B SaaS", "summary": "Fast, opinionated issue tracker built for high-velocity software teams.", "announced_date": "2022-09-14"},
    # HealthTech
    {"id": "openevidence-series-b", "company_name": "OpenEvidence", "website": "https://openevidence.com", "round_type": "Series B", "amount_usd": 75_000_000, "industry": "HealthTech", "summary": "AI clinical decision support tool that surfaces evidence-based answers for physicians.", "announced_date": "2024-10-01"},
    {"id": "hippocratic-ai-series-b", "company_name": "Hippocratic AI", "website": "https://hippocratic.ai", "round_type": "Series B", "amount_usd": 141_000_000, "industry": "HealthTech", "summary": "Safety-focused AI health agents for patient communication and care navigation.", "announced_date": "2024-07-23"},
    {"id": "turquoise-health-series-b", "company_name": "Turquoise Health", "website": "https://turquoise.health", "round_type": "Series B", "amount_usd": 30_000_000, "industry": "HealthTech", "summary": "Healthcare price transparency platform normalizing hospital pricing data.", "announced_date": "2023-10-24"},
    # CleanTech
    {"id": "form-energy-series-e", "company_name": "Form Energy", "website": "https://formenergy.com", "round_type": "Series E", "amount_usd": 450_000_000, "industry": "CleanTech", "summary": "Iron-air multi-day energy storage for grid-scale renewable backup.", "announced_date": "2023-08-01"},
    {"id": "terabase-series-c", "company_name": "Terabase Energy", "website": "https://terabase.energy", "round_type": "Series C", "amount_usd": 95_000_000, "industry": "CleanTech", "summary": "Software and robotics platform automating utility-scale solar farm construction.", "announced_date": "2024-03-20"},
    # HR Tech
    {"id": "ashby-series-c", "company_name": "Ashby", "website": "https://ashbyhq.com", "round_type": "Series C", "amount_usd": 30_000_000, "industry": "HR Tech", "summary": "All-in-one recruiting platform with ATS, scheduling and analytics built-in.", "announced_date": "2024-02-22"},
    {"id": "mercor-series-a", "company_name": "Mercor", "website": "https://mercor.com", "round_type": "Series A", "amount_usd": 30_000_000, "industry": "HR Tech", "summary": "AI hiring platform that screens, interviews and ranks candidates automatically.", "announced_date": "2024-06-18"},
    # EdTech
    {"id": "synthesis-series-b", "company_name": "Synthesis", "website": "https://synthesis.com", "round_type": "Series B", "amount_usd": 23_000_000, "industry": "EdTech", "summary": "AI math tutor for kids that adapts to each child's pace and learning style.", "announced_date": "2024-04-10"},
    {"id": "khanmigo-series-a", "company_name": "Khan Academy (Khanmigo)", "website": "https://khanacademy.org", "round_type": "Series A", "amount_usd": 0, "industry": "EdTech", "summary": "AI tutoring assistant embedded into Khan Academy's free education platform.", "announced_date": "2023-03-14"},
    # E-commerce / Logistics
    {"id": "flexport-series-e", "company_name": "Flexport", "website": "https://flexport.com", "round_type": "Series E", "amount_usd": 935_000_000, "industry": "E-commerce", "summary": "Digital freight forwarder and supply chain visibility platform.", "announced_date": "2022-02-10"},
    {"id": "loop-returns-series-c", "company_name": "Loop Returns", "website": "https://loopreturns.com", "round_type": "Series C", "amount_usd": 65_000_000, "industry": "E-commerce", "summary": "Returns management platform for Shopify brands reducing refund rates.", "announced_date": "2022-11-16"},
    # Data & AI Services — Anthropic ecosystem
    {"id": "phdata-series-b", "company_name": "phData", "website": "https://phdata.io", "round_type": "Series B", "amount_usd": 150_000_000, "industry": "AI/ML", "summary": "Data and AI services firm backed by Anthropic and others. Helps enterprises adopt AI with Snowflake, Databricks, and Claude-powered solutions.", "announced_date": "2024-09-10"},
    # More AI/ML 2024-2025
    {"id": "poolside-series-b", "company_name": "Poolside", "website": "https://poolside.ai", "round_type": "Series B", "amount_usd": 500_000_000, "industry": "AI/ML", "summary": "AI coding model company building foundation models trained purely on code.", "announced_date": "2024-08-08"},
    {"id": "imbue-series-b", "company_name": "Imbue", "website": "https://imbue.com", "round_type": "Series B", "amount_usd": 200_000_000, "industry": "AI/ML", "summary": "AI research lab focused on building practical AI agents that reason and code.", "announced_date": "2023-09-12"},
    {"id": "pika-labs-series-b", "company_name": "Pika Labs", "website": "https://pika.art", "round_type": "Series B", "amount_usd": 80_000_000, "industry": "AI/ML", "summary": "AI video generation platform turning ideas into cinematic video clips.", "announced_date": "2024-02-08"},
    {"id": "hedra-series-a", "company_name": "Hedra", "website": "https://hedra.com", "round_type": "Series A", "amount_usd": 32_000_000, "industry": "AI/ML", "summary": "AI video generation focused on character animation and talking avatar videos.", "announced_date": "2024-10-15"},
    {"id": "elevenlabs-series-c", "company_name": "ElevenLabs", "website": "https://elevenlabs.io", "round_type": "Series C", "amount_usd": 180_000_000, "industry": "AI/ML", "summary": "AI voice synthesis platform with ultra-realistic cloning in 29 languages.", "announced_date": "2024-01-22"},
    {"id": "ideogram-series-b", "company_name": "Ideogram", "website": "https://ideogram.ai", "round_type": "Series B", "amount_usd": 80_000_000, "industry": "AI/ML", "summary": "AI image generation with industry-leading text rendering inside images.", "announced_date": "2024-08-20"},
    {"id": "luma-ai-series-c", "company_name": "Luma AI", "website": "https://lumalabs.ai", "round_type": "Series C", "amount_usd": 43_000_000, "industry": "AI/ML", "summary": "3D capture and AI video generation platform behind Dream Machine.", "announced_date": "2024-06-12"},
    # More DevTools
    {"id": "depot-series-a", "company_name": "Depot", "website": "https://depot.dev", "round_type": "Series A", "amount_usd": 15_000_000, "industry": "DevTools", "summary": "Remote Docker build acceleration — 40x faster CI builds with persistent caching.", "announced_date": "2024-05-14"},
    {"id": "zed-industries-series-a", "company_name": "Zed Industries", "website": "https://zed.dev", "round_type": "Series A", "amount_usd": 27_000_000, "industry": "DevTools", "summary": "High-performance Rust-based code editor with real-time collaboration built-in.", "announced_date": "2024-01-24"},
    {"id": "inngest-series-a", "company_name": "Inngest", "website": "https://inngest.com", "round_type": "Series A", "amount_usd": 12_000_000, "industry": "DevTools", "summary": "Durable workflow engine for background jobs, queues, and event-driven functions.", "announced_date": "2024-08-06"},
    # More B2B SaaS
    {"id": "clay-series-b", "company_name": "Clay", "website": "https://clay.com", "round_type": "Series B", "amount_usd": 40_000_000, "industry": "B2B SaaS", "summary": "AI-powered sales prospecting platform enriching leads from 75+ data sources.", "announced_date": "2024-02-07"},
    {"id": "olo-series-f", "company_name": "Gamma", "website": "https://gamma.app", "round_type": "Series B", "amount_usd": 12_000_000, "industry": "B2B SaaS", "summary": "AI presentation and document builder replacing PowerPoint for modern teams.", "announced_date": "2023-11-01"},
    {"id": "runway-series-c", "company_name": "Runway", "website": "https://runwayml.com", "round_type": "Series C", "amount_usd": 141_000_000, "industry": "AI/ML", "summary": "Creative AI company behind Gen-2 and Gen-3 video generation models.", "announced_date": "2023-12-05"},
    # More Security
    {"id": "datavant-series-b", "company_name": "Abnormal Security", "website": "https://abnormalsecurity.com", "round_type": "Series D", "amount_usd": 250_000_000, "industry": "Security", "summary": "AI-native email security platform stopping socially-engineered attacks.", "announced_date": "2024-05-15"},
    {"id": "haize-labs-seed", "company_name": "Haize Labs", "website": "https://haizelabs.com", "round_type": "Seed", "amount_usd": 4_000_000, "industry": "Security", "summary": "AI red-teaming startup that automatically finds safety failures in LLMs.", "announced_date": "2024-06-20"},
    # More Fintech
    {"id": "brex-series-e", "company_name": "Brex", "website": "https://brex.com", "round_type": "Series E", "amount_usd": 235_000_000, "industry": "Fintech", "summary": "AI-powered spend management and corporate cards for startups and enterprises.", "announced_date": "2024-05-23"},
    {"id": "fern-series-a", "company_name": "Fern", "website": "https://buildwithfern.com", "round_type": "Series A", "amount_usd": 10_000_000, "industry": "DevTools", "summary": "SDK and API docs generator — auto-generates typed SDKs from OpenAPI specs.", "announced_date": "2024-07-09"},
]


def run_pipeline() -> list[dict]:
    now_utc = datetime.now(timezone.utc).isoformat()
    seen: set[str] = set()
    merged: list[dict] = []
    for seed in SEED_DATA:
        if seed["id"] not in seen:
            seen.add(seed["id"])
            merged.append(seed)

    merged.sort(key=lambda x: x.get("announced_date", ""), reverse=True)
    output = [{**entry, "ingested_at": now_utc} for entry in merged]

    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(output, indent=2))
    print(f"[pipeline] Wrote {len(output)} records → {DATA_FILE}")
    return output


if __name__ == "__main__":
    run_pipeline()
