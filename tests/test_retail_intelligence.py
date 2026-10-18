"""
Automated Retail & Commerce Intelligence Tests
Covers:
  - Feature A: Product Discovery & Grounded Ranking
  - Feature B: Personalization & Preference Matching
  - Feature C: Inventory Intelligence & Low-Stock Alerts
  - Feature D: Demand Forecasting & Sparse Data Transparency
  - Feature E: Basket Analysis & Customer Segmentation
  - Feature F: Grounded Business Decision Assistant
"""

import pytest
from services.repository import RepositoryService
from services.retail_intelligence import (
    RetailDiscoveryService,
    DiscoveryQuery,
    InventoryIntelligenceService,
    DemandForecastService,
    AnalyticsService,
    BusinessDecisionAssistantService
)

@pytest.fixture(autouse=True)
def init_repo():
    RepositoryService.initialize()

def test_feature_a_product_discovery():
    """Verify semantic and attribute-based catalog product discovery."""
    dq = DiscoveryQuery(
        query_text="Paithani Silk Saree",
        category="Textiles & Apparel",
        max_budget=50000.0,
        min_stock=1
    )
    results = RetailDiscoveryService.discover_products(dq)

    assert len(results) > 0
    top = results[0]
    assert top.match_score > 0
    assert "Paithani" in top.product["name"] or "Saree" in top.product["name"]
    assert len(top.relevance_reasons) > 0

def test_feature_b_personalization():
    """Verify that user preferences boost relevant craft categories."""
    user_id = "test-user-personalization"
    RepositoryService.save_customer_preferences(user_id, {
        "preferred_categories": ["Pottery & Ceramics"],
        "consent_given": True
    })

    # Search without category filter: Pottery items should receive personalization boost
    dq = DiscoveryQuery(
        query_text="decor vase",
        user_id=user_id
    )
    results = RetailDiscoveryService.discover_products(dq)

    pottery_items = [r for r in results if "pottery" in r.product.get("category", "").lower()]
    if pottery_items:
        reasons = " ".join(pottery_items[0].relevance_reasons)
        assert "aligned with your preferred craft categories" in reasons.lower()

def test_feature_c_inventory_intelligence():
    """Verify low stock indicators and replenishment recommendations."""
    health = InventoryIntelligenceService.get_inventory_health()

    assert "total_inventory_units" in health
    assert "low_stock_count" in health
    assert health["total_inventory_units"] > 0

    if health["low_stock_items"]:
        item = health["low_stock_items"][0]
        assert item["available_stock"] <= InventoryIntelligenceService.LOW_STOCK_THRESHOLD
        assert item["reorder_suggested_units"] > 0

def test_feature_d_demand_forecasting():
    """Verify 30-day baseline moving average demand projection with honest limitations."""
    forecast = DemandForecastService.generate_forecast(horizon_days=30)

    assert forecast["forecast_horizon_days"] == 30
    assert forecast["projected_units_demanded"] > 0
    assert forecast["projected_revenue_inr"] > 0
    assert forecast["confidence"] in ("HIGH", "MEDIUM", "LOW")
    assert "Methodology" in forecast["notes"] or "Forecast" in forecast["notes"]

def test_feature_e_basket_analysis_and_segmentation():
    """Verify co-purchased basket pairs and behavioral customer segments."""
    analytics = AnalyticsService.get_commerce_analytics()

    assert "top_selling_products" in analytics
    assert "market_basket_pairings" in analytics
    assert "customer_segments" in analytics

    # Validate customer segmentation cohorts
    segments = analytics["customer_segments"]
    assert "Bulk Institutional Buyers" in segments
    assert "Boutique Retailers" in segments
    assert "Single-Order Buyers" in segments

    # Validate market basket pairs
    pairs = analytics["market_basket_pairings"]
    assert len(pairs) > 0
    assert "+" in pairs[0]["pairing"]

def test_feature_f_business_decision_assistant():
    """Verify that business queries are answered using grounded operational data."""
    res = BusinessDecisionAssistantService.answer_business_query(
        question="Which items should I replenish first to prevent stockouts?"
    )

    assert res["success"] is True
    assert res["answer"] is not None
    assert len(res["answer"]) > 20
    assert "grounding_data" in res
    assert "low_stock_items" in res["grounding_data"]["inventory_summary"]
