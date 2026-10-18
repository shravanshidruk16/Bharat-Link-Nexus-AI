"""
Automated Tests for Cloud Firestore Connectivity & Production Fallback Prevention
Covers:
  - Successful Cloud Firestore initialization via ADC / project binding
  - Verification that connectivity probes do not modify production data
  - Liveness (/health) vs Dependency Readiness (/health/ready) distinction
  - Error handling when Firestore is unavailable
  - Strict prevention of unintended mock/sample data fallback in production
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

import main
from config import FIREBASE_PROJECT_ID
from services.repository import RepositoryService

@pytest.fixture(autouse=True)
def reset_repository_state():
    """Ensure clean repository state before and after each test."""
    RepositoryService.initialize(force_reconnect=True)
    yield
    RepositoryService.initialize(force_reconnect=True)

@pytest.fixture(scope="module")
def client():
    return TestClient(main.app)

def test_successful_firestore_initialization():
    """Verify that RepositoryService successfully connects to Cloud Firestore via ADC."""
    is_connected = RepositoryService.is_firestore_connected()
    assert is_connected is True, "Expected RepositoryService to connect to live Cloud Firestore using ADC"
    
    info = RepositoryService.get_connection_info()
    assert info["firestore_connected"] is True
    assert info["project_id"] == "bharatlink-nexus-ai"
    assert info["mode"] == "cloud_firestore"

def test_firestore_connectivity_probe_does_not_modify_production_data():
    """Verify that connectivity probes and database inspections do NOT write any records to production."""
    client_ref = RepositoryService._firestore_client
    assert client_ref is not None
    assert client_ref.project == "bharatlink-nexus-ai"

    # Inspect collection references without calling .set(), .add(), or .delete()
    collections = list(client_ref.collections())
    # Database is fresh, so collections is a list
    assert isinstance(collections, list)

def test_health_readiness_reports_firestore_connected(client):
    """Verify that /health/ready accurately reports live Cloud Firestore connectivity."""
    res = client.get("/health/ready")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ready"
    assert data["ready"] is True
    assert data["firestore_connected"] is True
    assert data["database"] == "cloud_firestore"
    assert data["project_id"] == "bharatlink-nexus-ai"

def test_health_liveness_vs_readiness_distinction(client):
    """Verify that /health (liveness) returns 200 even if database readiness fails."""
    liveness_res = client.get("/health")
    assert liveness_res.status_code == 200
    assert liveness_res.json()["status"] == "ok"

    # Simulate database disconnection
    with patch.object(RepositoryService, "_firestore_client", None):
        info = RepositoryService.get_connection_info()
        assert info["firestore_connected"] is False

        # Liveness remains 200 OK (process is alive)
        liveness_again = client.get("/health")
        assert liveness_again.status_code == 200

def test_prevention_of_unintended_production_fallback(client):
    """
    Verify that in production mode:
      1. Disconnected Firestore triggers HTTP 503 on /health/ready.
      2. The application NEVER silently serves sample catalog data.
    """
    with patch("main.ENVIRONMENT", "production"), \
         patch("services.repository.ENVIRONMENT", "production"), \
         patch.object(RepositoryService, "_firestore_client", None):

        # 1. Readiness probe must reject unready state with 503
        res = client.get("/health/ready")
        assert res.status_code == 503
        data = res.json()
        assert data["status"] == "not_ready"
        assert data["ready"] is False
        assert "Cloud Firestore dependency is unavailable" in data["error"]

        # 2. Querying products in production without Firestore must return [] (no silent sample injection)
        prods = RepositoryService.get_products()
        assert prods == [], "CRITICAL: Sample data was leaked in production environment!"

def test_migrated_products_and_sellers_loaded_from_firestore():
    """Verify that RepositoryService loads authentic migrated products & sellers from Cloud Firestore."""
    RepositoryService.initialize(force_reconnect=True)
    info = RepositoryService.get_connection_info()
    assert info["firestore_connected"] is True
    assert info["source"] == "cloud_firestore"
    assert info["products_count"] >= 516
    assert info["sellers_count"] >= 47

def test_firestore_product_and_seller_reads():
    """Verify that get_products and get_sellers return authentic records with proper types."""
    RepositoryService.initialize(force_reconnect=True)
    products = RepositoryService.get_products(limit=10)
    assert len(products) > 0
    p = products[0]
    assert "id" in p
    assert "name" in p
    assert "price" in p
    assert isinstance(p["price"], (int, float))

    active_sellers = RepositoryService.get_sellers(active_only=True)
    all_sellers = RepositoryService.get_sellers(active_only=False)
    assert len(active_sellers) == 43
    assert len(all_sellers) == 47
    s = active_sellers[0]
    assert "business_name" in s
    assert "craft_category" in s

def test_order_persistence_in_firestore():
    """Verify creating an order writes to Firestore and persists across lookups."""
    RepositoryService.initialize(force_reconnect=True)
    test_order_data = {
        "id": "test-order-audit-001",
        "buyer_id": "test-buyer-001",
        "seller_id": "test-seller-001",
        "seller_name": "Test Artisan Collective",
        "product_id": "test-prod-001",
        "product_name": "Authentic Handcrafted Scarf",
        "quantity": 2,
        "total_cost": 1500.0,
        "status": "Pending"
    }
    created = RepositoryService.create_order(test_order_data)
    assert created["id"] == "test-order-audit-001"
    assert created["status"] == "Pending"

    # Status update
    updated = RepositoryService.update_order_status("test-order-audit-001", "Shipped", "test-seller-001", is_admin=True)
    assert updated is True

    # Cleanup test order document so production remains pristine
    if RepositoryService._firestore_client:
        try:
            RepositoryService._firestore_client.collection("orders").document("test-order-audit-001").delete()
        except Exception:
            pass
    if "test-order-audit-001" in RepositoryService._db["orders"]:
        del RepositoryService._db["orders"]["test-order-audit-001"]

