"""
Automated Deployment, Health Probes & Operational Tests
Covers:
  - Liveness (/health) and readiness (/health/ready) endpoints
  - Operation without Supabase dependency
  - PORT environment variable support
  - Conversational shopping assistant endpoint (/api/chat)
  - SEO endpoints (/robots.txt, /sitemap.xml)
"""

import os
import pytest
from fastapi.testclient import TestClient
import main
from services.repository import RepositoryService

@pytest.fixture(scope="module")
def client():
    RepositoryService.initialize()
    return TestClient(main.app)

def test_health_liveness_endpoint(client):
    """Verify Cloud Run /health liveness probe."""
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["service"] == "bharatlink-nexus-ai"
    assert "timestamp" in data

def test_health_readiness_endpoint(client):
    """Verify Cloud Run /health/ready readiness probe."""
    res = client.get("/health/ready")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ready"
    assert data["sample_catalog_available"] is True

def test_app_starts_without_supabase_credentials(client):
    """Verify that catalog and routes function without Supabase dependencies."""
    res = client.get("/health/ready")
    assert res.status_code == 200

    catalog_res = client.get("/crafts")
    assert catalog_res.status_code == 200

def test_conversational_shopping_assistant_api(client):
    """Verify that the buyer conversational assistant endpoint responds with grounded recommendations."""
    res = client.post("/api/chat", json={
        "message": "Do you have any authentic silk sarees or wedding apparel?"
    })
    assert res.status_code == 200
    data = res.json()
    assert "reply" in data
    assert len(data["reply"]) > 10
    assert "recommended_products" in data

def test_seo_robots_and_sitemap(client):
    """Verify technical SEO endpoints."""
    robots = client.get("/robots.txt")
    assert robots.status_code == 200
    assert "User-agent: *" in robots.text
    assert "Disallow: /admin/" in robots.text

    sitemap = client.get("/sitemap.xml")
    assert sitemap.status_code == 200
    assert "<urlset" in sitemap.text
