# BharatLink Nexus AI — Testing & Quality Assurance Guide

## 1. Testing Framework Overview

BharatLink Nexus AI uses `pytest` and `fastapi.testclient.TestClient` to execute end-to-end automated tests across all operational tiers:
- **Security & Authorization**
- **Database & Repository Operations**
- **AI Providers & LangGraph Workflow**
- **Retail & Commerce Intelligence Services**
- **Deployment & Production Readiness**

---

## 2. Running the Test Suite

Execute the tests from the repository root:

```bash
# Run all automated tests
pytest -v

# Run specific test suites
pytest tests/test_security.py -v
pytest tests/test_database.py -v
pytest tests/test_ai_provider.py -v
pytest tests/test_retail_intelligence.py -v
pytest tests/test_deployment.py -v

# Run with test coverage
pytest --cov=services --cov=agents tests/
```

---

## 3. Test Coverage Matrix

### 3.1 Security Tests (`tests/test_security.py`)
- `test_unauthenticated_access_denied`: Confirms protected endpoints (`/procure`, `/dashboard`, `/history`, `/seller-central/dashboard`) redirect unauthenticated visitors or reject requests with `401/303`.
- `test_invalid_token_rejected`: Confirms forged or invalid tokens fail verification.
- `test_buyer_cannot_access_other_buyer_data`: Enforces tenant isolation on procurement history and profile endpoints.
- `test_seller_cannot_modify_other_seller_product`: Confirms that a seller cannot update or delete products belonging to a different seller ID.
- `test_non_admin_cannot_access_admin_dashboard`: Confirms that non-admin accounts cannot access `/admin/dashboard` or `/seller-central/admin/dashboard`.
- `test_prevent_self_assigned_admin_role`: Confirms that role escalation via form inputs or cookies is prevented.

### 3.2 Database & Repository Tests (`tests/test_database.py`)
- `test_repository_crud`: Tests product creation, querying by ID, category filtering, and updates.
- `test_transactional_stock_decrement`: Verifies that stock decrementing succeeds when stock is available.
- `test_oversell_prevention`: Proves that concurrent/excess stock decrements fail safely without overselling below 0.
- `test_inventory_movement_audit_log`: Verifies that every stock adjustment creates an audit log entry in `inventory_movements`.
- `test_pagination_and_filtering`: Tests product catalog pagination and category/region filters.

### 3.3 AI Provider Tests (`tests/test_ai_provider.py`)
- `test_gemini_provider_invocation`: Verifies that `services/ai_provider.py` invokes Gemini with configured model (`gemini-2.5-flash`).
- `test_groq_fallback_when_configured`: Tests Groq invocation when explicitly selected.
- `test_structured_json_extraction`: Verifies that markdown-wrapped or malformed JSON responses are safely extracted and sanitized.
- `test_no_api_keys_leaked_in_logs`: Validates that logger outputs and client errors never print raw API keys.
- `test_langgraph_workflow_empty_catalog`: Verifies that when no matching products exist in the catalog, the workflow returns a structured "Product Not Found" narrative rather than hallucinating products.

### 3.4 Retail Intelligence Tests (`tests/test_retail_intelligence.py`)
- `test_product_discovery_semantic_ranking`: Verifies that natural language search ranks relevant items by category and attributes.
- `test_personalization_preferences`: Verifies that customer preferences re-rank recommendations according to saved category affinities.
- `test_inventory_intelligence_low_stock_alerts`: Verifies low stock detection when `available_stock < threshold`.
- `test_demand_forecasting_with_sales_history`: Verifies moving average trend forecasting with statistical confidence bounds.
- `test_demand_forecasting_sparse_data_honesty`: Confirms that empty or insufficient history explicitly reports confidence limitations.
- `test_basket_analysis_co_purchases`: Tests co-purchase pair discovery from multi-item sales transactions.

### 3.5 Deployment & Health Tests (`tests/test_deployment.py`)
- `test_health_endpoint`: Tests `/health` probe returns status `ok`.
- `test_readiness_probe`: Tests `/health/ready` probe verifies database connectivity.
- `test_port_environment_variable_compliance`: Tests that the application starts cleanly when `$PORT` is set.
- `test_app_starts_without_supabase`: Proves that the application functions without requiring Supabase credentials.
