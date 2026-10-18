"""
Automated Security & Tenant Isolation Tests
Covers:
  - Unauthenticated access rejection
  - Forged/invalid session signature rejection
  - Buyer and seller tenant isolation
  - Admin endpoint protection
  - Privilege escalation defense
"""

import pytest
from fastapi.testclient import TestClient
import main
from services.firebase_service import FirebaseAuthService
from services.repository import RepositoryService, UnauthorizedTenantError

@pytest.fixture(scope="module")
def client():
    RepositoryService.initialize()
    return TestClient(main.app)

def test_unauthenticated_buyer_redirected_to_login(client):
    """Unauthenticated users attempting to access /procure must be redirected to /login."""
    response = client.get("/procure", follow_redirects=False)
    assert response.status_code in (302, 303, 307)
    assert "/login" in response.headers.get("location", "")

def test_unauthenticated_seller_redirected(client):
    """Unauthenticated users attempting to access seller dashboard must be redirected."""
    response = client.get("/seller-central/dashboard", follow_redirects=False)
    assert response.status_code in (302, 303, 307)
    assert "/seller-central/login" in response.headers.get("location", "")

def test_forged_session_cookie_rejected(client):
    """A forged or tampered session cookie must be rejected."""
    # Create fake cookie without valid HMAC signature
    fake_cookie = "eyJlbWFpbCI6ICJhZG1pbkBoYWNrZXIuY29tIiwgInJvbGUiOiAiYWRtaW4ifQ.invalidsignature123"
    client.cookies.set("buyer_session", fake_cookie)

    response = client.get("/procure", follow_redirects=False)
    assert response.status_code in (302, 303, 307)
    assert "/login" in response.headers.get("location", "")
    client.cookies.clear()

def test_seller_cannot_modify_other_seller_product():
    """A seller cannot modify a product owned by a different seller ID."""
    seller1_id = "seller-guild-001"
    seller2_id = "seller-guild-002"

    # Create product for seller 1
    prod = RepositoryService.add_product({
        "name": "Paithani Silk Scarf",
        "category": "Textiles & Apparel",
        "price": 4500.0,
        "available_stock": 10
    }, seller_id=seller1_id)

    # Attempt update as seller 2 (must raise UnauthorizedTenantError)
    with pytest.raises(UnauthorizedTenantError):
        RepositoryService.update_product(
            product_id=prod["id"],
            update_data={"price": 999.0},
            actor_seller_id=seller2_id,
            is_admin=False
        )

def test_seller_cannot_delete_other_seller_product():
    """A seller cannot delete a product owned by a different seller ID."""
    seller1_id = "seller-guild-001"
    seller2_id = "seller-guild-002"

    prod = RepositoryService.add_product({
        "name": "Kolhapuri Leather Belt",
        "category": "Footwear & Leather",
        "price": 1200.0,
        "available_stock": 5
    }, seller_id=seller1_id)

    with pytest.raises(UnauthorizedTenantError):
        RepositoryService.delete_product(
            product_id=prod["id"],
            actor_seller_id=seller2_id,
            is_admin=False
        )

def test_non_admin_cannot_access_admin_dashboard(client):
    """A normal buyer cannot access /admin/dashboard."""
    buyer_user = {
        "id": "buyer-test-101",
        "email": "buyer@test.com",
        "role": "buyer",
        "full_name": "Test Buyer"
    }
    valid_session = FirebaseAuthService.create_signed_session(buyer_user)
    client.cookies.set("buyer_session", valid_session)

    response = client.get("/admin/dashboard", follow_redirects=False)
    # Must redirect to login or deny access
    assert response.status_code in (302, 303, 403)
    client.cookies.clear()

def test_non_admin_cannot_access_seller_admin_dashboard(client):
    """A normal seller cannot access /seller-central/admin/dashboard."""
    seller_user = {
        "id": "seller-test-202",
        "email": "artisan@test.com",
        "role": "seller",
        "seller_id": "seller-guild-001"
    }
    valid_session = FirebaseAuthService.create_signed_session(seller_user)
    client.cookies.set("seller_session", valid_session)

    response = client.get("/seller-central/admin/dashboard", follow_redirects=False)
    assert response.status_code in (302, 303, 403)
    client.cookies.clear()

def test_prevent_unauthorized_role_modification():
    """Only verified administrators can update user roles."""
    with pytest.raises(UnauthorizedTenantError):
        RepositoryService.update_user_role(
            user_id="target-user-001",
            new_role="admin",
            admin_user_id="non-admin-user-002"
        )

def test_expired_session_rejected(client):
    """Sessions with an expired timestamp must be rejected."""
    user = {
        "id": "buyer-exp-001",
        "email": "buyer@test.com",
        "role": "buyer"
    }
    # Create expired token (negative max age)
    expired_token = FirebaseAuthService.create_signed_session(user, max_age_seconds=-100)
    client.cookies.set("buyer_session", expired_token)

    response = client.get("/procure", follow_redirects=False)
    assert response.status_code in (302, 303, 307)
    assert "/login" in response.headers.get("location", "")
    client.cookies.clear()
