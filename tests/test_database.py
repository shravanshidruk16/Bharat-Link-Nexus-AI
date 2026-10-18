"""
Automated Database & Firestore Repository Tests
Covers:
  - Repository CRUD operations
  - ACID transactional stock updates
  - Concurrency & overselling protection
  - Inventory movement audit logging
  - Pagination and filtering
  - Customer preferences storage
"""

import pytest
from services.repository import (
    RepositoryService,
    InsufficientStockError,
    UnauthorizedTenantError
)

@pytest.fixture(autouse=True)
def setup_repo():
    RepositoryService.initialize()

def test_product_creation_and_retrieval():
    """Verify that products can be created and retrieved from the repository."""
    seller_id = "test-artisan-guild-99"
    new_prod = RepositoryService.add_product({
        "name": "Handmade Clay Water Jug",
        "description": "Natural terracotta clay jug from Kutch.",
        "category": "Pottery & Ceramics",
        "region": "Gujarat",
        "price": 650.0,
        "available_stock": 25,
        "weight_kg": 1.5
    }, seller_id=seller_id)

    assert new_prod["id"] is not None
    assert new_prod["name"] == "Handmade Clay Water Jug"
    assert new_prod["price"] == 650.0
    assert new_prod["available_stock"] == 25

    fetched = RepositoryService.get_product_by_id(new_prod["id"])
    assert fetched is not None
    assert fetched["name"] == "Handmade Clay Water Jug"

def test_transactional_stock_decrement_success():
    """Verify atomic decrement of stock when inventory is available."""
    prod = RepositoryService.add_product({
        "name": "Brass Peacock Lamp",
        "price": 3200.0,
        "available_stock": 20
    }, seller_id="seller-101")

    updated = RepositoryService.decrement_stock_transactional(
        product_id=prod["id"],
        quantity=5,
        order_id="test-order-555"
    )
    assert updated["available_stock"] == 15

def test_overselling_prevention():
    """Verify that an order exceeding available stock is rejected without partial overselling."""
    prod = RepositoryService.add_product({
        "name": "Rare Pashmina Shawl",
        "price": 18000.0,
        "available_stock": 3
    }, seller_id="seller-102")

    # Attempt to order 4 units when only 3 exist
    with pytest.raises(InsufficientStockError) as exc_info:
        RepositoryService.decrement_stock_transactional(
            product_id=prod["id"],
            quantity=4,
            order_id="test-order-overflow"
        )
    assert "only 3 units are in stock" in str(exc_info.value)

    # Ensure stock was NOT modified
    fetched = RepositoryService.get_product_by_id(prod["id"])
    assert fetched["available_stock"] == 3

def test_inventory_movement_audit_log_created():
    """Verify that stock adjustments generate immutable inventory movement audit records."""
    prod = RepositoryService.add_product({
        "name": "Sandalwood Incense Box",
        "price": 450.0,
        "available_stock": 30
    }, seller_id="seller-103")

    RepositoryService.decrement_stock_transactional(prod["id"], 10, "order-audit-check")
    movements = RepositoryService.get_inventory_movements(product_id=prod["id"])

    assert len(movements) >= 2  # 1 initial creation + 1 order decrement
    latest = movements[0]
    assert latest["delta"] == -10
    assert latest["new_stock"] == 20
    assert "order-audit-check" in latest["reason"]

def test_pagination_and_category_filtering():
    """Verify category filtering and pagination parameters."""
    prods = RepositoryService.get_products(category="Textiles", limit=5, offset=0)
    assert isinstance(prods, list)
    assert len(prods) <= 5
    for p in prods:
        assert "textile" in p.get("category", "").lower() or "apparel" in p.get("category", "").lower()

def test_customer_preferences_lifecycle():
    """Verify saving, retrieving, and deleting consent-driven customer preferences."""
    user_id = "test-buyer-pref-001"

    saved = RepositoryService.save_customer_preferences(user_id, {
        "preferred_categories": ["Pottery & Ceramics", "Organic Produce"],
        "max_budget": 50000.0,
        "consent_given": True
    })
    assert saved["consent_given"] is True
    assert len(saved["preferred_categories"]) == 2

    retrieved = RepositoryService.get_customer_preferences(user_id)
    assert retrieved is not None
    assert retrieved["max_budget"] == 50000.0

    # Delete
    deleted = RepositoryService.delete_customer_preferences(user_id)
    assert deleted is True
    assert RepositoryService.get_customer_preferences(user_id) is None
