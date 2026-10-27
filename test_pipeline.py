"""Tests for pipeline normalization and FastAPI endpoints."""

import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from pipeline import parse_funding_amount
from main import app, DATA_FILE

client = TestClient(app)

# ──────────────────────────────────────────────────────────────────────────────
# parse_funding_amount tests
# ──────────────────────────────────────────────────────────────────────────────

def test_parse_millions():
    assert parse_funding_amount("$2.5M") == 2_500_000

def test_parse_thousands():
    assert parse_funding_amount("$750K") == 750_000

def test_parse_billions():
    assert parse_funding_amount("$1B") == 1_000_000_000

def test_parse_euros():
    result = parse_funding_amount("€3M")
    assert result is not None
    assert result > 3_000_000  # EUR > USD conversion applied

def test_parse_undisclosed():
    assert parse_funding_amount("Undisclosed") is None

def test_parse_empty_string():
    assert parse_funding_amount("") is None

def test_parse_none():
    assert parse_funding_amount(None) is None

def test_parse_comma_separated():
    assert parse_funding_amount("$1,500K") == 1_500_000

# ──────────────────────────────────────────────────────────────────────────────
# API endpoint tests (require data/latest_funding.json to exist)
# ──────────────────────────────────────────────────────────────────────────────

SAMPLE_DATA = [
    {
        "id": "test-company-1",
        "company_name": "TestCo AI",
        "website": "https://testco.ai",
        "round_type": "Seed",
        "amount_usd": 5_000_000,
        "industry": "AI/ML",
        "summary": "AI platform for enterprises.",
        "announced_date": "2024-01-15",
        "ingested_at": "2024-01-15T12:00:00+00:00",
    },
    {
        "id": "test-company-2",
        "company_name": "FinFlow",
        "website": "https://finflow.io",
        "round_type": "Series A",
        "amount_usd": 15_000_000,
        "industry": "Fintech",
        "summary": "Modern payments infrastructure for SMBs.",
        "announced_date": "2024-01-10",
        "ingested_at": "2024-01-10T08:00:00+00:00",
    },
]


@pytest.fixture(autouse=True)
def write_sample_data(tmp_path, monkeypatch):
    """Redirect DATA_FILE to a temp directory and seed it with sample data."""
    import main
    import pipeline
    test_data_file = tmp_path / "data" / "latest_funding.json"
    test_data_file.parent.mkdir(parents=True)
    test_data_file.write_text(json.dumps(SAMPLE_DATA, indent=2))
    monkeypatch.setattr(main, "DATA_FILE", test_data_file)
    monkeypatch.setattr(pipeline, "DATA_FILE", test_data_file)
    yield


def test_health_returns_200():
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["total_companies"] == len(SAMPLE_DATA)


def test_leads_returns_200():
    resp = client.get("/v1/leads")
    assert resp.status_code == 200
    leads = resp.json()
    assert isinstance(leads, list)
    assert len(leads) == len(SAMPLE_DATA)


def test_leads_filter_by_stage():
    resp = client.get("/v1/leads?stage=Seed")
    assert resp.status_code == 200
    leads = resp.json()
    assert all(l["round_type"] == "Seed" for l in leads)
    assert len(leads) == 1


def test_leads_filter_by_industry():
    resp = client.get("/v1/leads?industry=Fintech")
    assert resp.status_code == 200
    leads = resp.json()
    assert all("Fintech" in l["industry"] for l in leads)


def test_leads_filter_min_funding():
    resp = client.get("/v1/leads?min_funding_usd=10000000")
    assert resp.status_code == 200
    leads = resp.json()
    assert all(l["amount_usd"] >= 10_000_000 for l in leads)


def test_leads_limit():
    resp = client.get("/v1/leads?limit=1")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_stats_returns_200():
    resp = client.get("/v1/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert "total_vc_tracked_usd" in body
    assert "by_industry" in body
    assert "by_round_type" in body
    assert body["total_companies"] == len(SAMPLE_DATA)
    assert body["total_vc_tracked_usd"] == 5_000_000 + 15_000_000


def test_schema_fields_present():
    resp = client.get("/v1/leads")
    lead = resp.json()[0]
    required = {"id", "company_name", "website", "round_type", "industry", "summary", "announced_date", "ingested_at"}
    assert required.issubset(lead.keys())
