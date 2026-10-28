"""Tests for pipeline normalization and FastAPI endpoints."""

import json
import pytest
from fastapi.testclient import TestClient

from pipeline import parse_funding_amount
from main import app

client = TestClient(app)

# ──────────────────────────────────────────────────────────────────────────────
# parse_funding_amount
# ──────────────────────────────────────────────────────────────────────────────

def test_parse_millions():
    assert parse_funding_amount("$2.5M") == 2_500_000

def test_parse_thousands():
    assert parse_funding_amount("$750K") == 750_000

def test_parse_billions():
    assert parse_funding_amount("$1B") == 1_000_000_000

def test_parse_euros():
    result = parse_funding_amount("€3M")
    assert result is not None and result > 3_000_000

def test_parse_undisclosed():
    assert parse_funding_amount("Undisclosed") is None

def test_parse_empty_string():
    assert parse_funding_amount("") is None

def test_parse_none():
    assert parse_funding_amount(None) is None

def test_parse_comma_separated():
    assert parse_funding_amount("$1,500K") == 1_500_000

def test_parse_large_round():
    assert parse_funding_amount("$6.6B") == 6_600_000_000

# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────

SAMPLE_DATA = [
    {
        "id": "test-ai-1",
        "company_name": "TestCo AI",
        "website": "https://testco.ai",
        "round_type": "Seed",
        "amount_usd": 5_000_000,
        "industry": "AI/ML",
        "summary": "AI platform for enterprises.",
        "announced_date": "2024-06-15",
        "ingested_at": "2024-06-15T12:00:00+00:00",
    },
    {
        "id": "test-fintech-2",
        "company_name": "FinFlow",
        "website": "https://finflow.io",
        "round_type": "Series A",
        "amount_usd": 15_000_000,
        "industry": "Fintech",
        "summary": "Modern payments infrastructure for SMBs.",
        "announced_date": "2024-01-10",
        "ingested_at": "2024-01-10T08:00:00+00:00",
    },
    {
        "id": "test-security-3",
        "company_name": "ShieldOps",
        "website": "https://shieldops.io",
        "round_type": "Series B",
        "amount_usd": 60_000_000,
        "industry": "Security",
        "summary": "Zero-trust security platform for enterprise cloud environments.",
        "announced_date": "2024-03-20",
        "ingested_at": "2024-03-20T08:00:00+00:00",
    },
]


@pytest.fixture(autouse=True)
def write_sample_data(tmp_path, monkeypatch):
    import main, pipeline
    test_file = tmp_path / "data" / "latest_funding.json"
    test_file.parent.mkdir(parents=True)
    test_file.write_text(json.dumps(SAMPLE_DATA, indent=2))
    monkeypatch.setattr(main, "DATA_FILE", test_file)
    monkeypatch.setattr(pipeline, "DATA_FILE", test_file)


# ──────────────────────────────────────────────────────────────────────────────
# Health
# ──────────────────────────────────────────────────────────────────────────────

def test_health_200():
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["total_companies"] == len(SAMPLE_DATA)

# ──────────────────────────────────────────────────────────────────────────────
# /v1/leads
# ──────────────────────────────────────────────────────────────────────────────

def test_leads_200():
    resp = client.get("/v1/leads")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == len(SAMPLE_DATA)
    assert len(body["results"]) == len(SAMPLE_DATA)

def test_leads_filter_stage():
    resp = client.get("/v1/leads?stage=Seed")
    assert resp.status_code == 200
    body = resp.json()
    assert all(l["round_type"] == "Seed" for l in body["results"])

def test_leads_filter_industry():
    resp = client.get("/v1/leads?industry=Fintech")
    assert resp.status_code == 200
    assert all("Fintech" in l["industry"] for l in resp.json()["results"])

def test_leads_filter_min_funding():
    resp = client.get("/v1/leads?min_funding_usd=10000000")
    assert resp.status_code == 200
    assert all(l["amount_usd"] >= 10_000_000 for l in resp.json()["results"])

def test_leads_filter_max_funding():
    resp = client.get("/v1/leads?max_funding_usd=10000000")
    assert resp.status_code == 200
    assert all((l["amount_usd"] or 0) <= 10_000_000 for l in resp.json()["results"])

def test_leads_search():
    resp = client.get("/v1/leads?search=payments")
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert any("payment" in l["summary"].lower() for l in results)

def test_leads_pagination():
    resp = client.get("/v1/leads?limit=2&offset=0")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["results"]) == 2
    assert body["total"] == len(SAMPLE_DATA)

def test_leads_offset():
    resp = client.get("/v1/leads?limit=1&offset=1")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["results"]) == 1
    assert body["offset"] == 1

def test_leads_x_total_count_header():
    resp = client.get("/v1/leads")
    assert "x-total-count" in resp.headers
    assert int(resp.headers["x-total-count"]) == len(SAMPLE_DATA)

def test_leads_sorted_by_date_desc():
    resp = client.get("/v1/leads")
    dates = [l["announced_date"] for l in resp.json()["results"]]
    assert dates == sorted(dates, reverse=True)

def test_leads_schema_fields():
    resp = client.get("/v1/leads")
    lead = resp.json()["results"][0]
    required = {"id", "company_name", "website", "round_type", "industry", "summary", "announced_date", "ingested_at"}
    assert required.issubset(lead.keys())

# ──────────────────────────────────────────────────────────────────────────────
# /v1/company/:id
# ──────────────────────────────────────────────────────────────────────────────

def test_get_company_found():
    resp = client.get("/v1/company/test-ai-1")
    assert resp.status_code == 200
    assert resp.json()["company_name"] == "TestCo AI"

def test_get_company_not_found():
    resp = client.get("/v1/company/does-not-exist")
    assert resp.status_code == 404

# ──────────────────────────────────────────────────────────────────────────────
# /v1/stats
# ──────────────────────────────────────────────────────────────────────────────

def test_stats_200():
    resp = client.get("/v1/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_companies"] == len(SAMPLE_DATA)
    assert body["total_vc_tracked_usd"] == 5_000_000 + 15_000_000 + 60_000_000
    assert "total_vc_tracked_formatted" in body
    assert "by_industry" in body
    assert "by_round_type" in body

def test_stats_formatted_amount():
    resp = client.get("/v1/stats")
    fmt = resp.json()["total_vc_tracked_formatted"]
    assert fmt.startswith("$") and ("M" in fmt or "B" in fmt or "K" in fmt)
