"""
Automated AI Provider & Multi-Agent Tests
Covers:
  - Gemini provider execution & model selection
  - Groq secondary provider execution
  - Structured JSON parsing & error resilience
  - API key masking (zero key leakage)
  - LangGraph workflow execution with grounded catalog & out-of-scope queries
"""

import pytest
from services.ai_provider import AIProviderService, set_mock_mode
from agents.workflow import build_workflow

@pytest.fixture(autouse=True)
def clean_mock():
    set_mock_mode(False)
    yield
    set_mock_mode(False)

def test_ai_provider_gemini_generation():
    """Verify that Gemini or resilient secondary provider generates valid responses."""
    res = AIProviderService.generate("Reply with exactly: PONG", temperature=0.1)
    assert res.success is True
    assert "PONG" in res.content.upper()
    assert res.provider in ("gemini", "groq")
    assert bool(res.model)

def test_ai_provider_structured_json():
    """Verify structured JSON extraction from AI responses."""
    parsed, res = AIProviderService.generate_json(
        prompt="Generate a JSON object with keys 'status' set to 'active' and 'code' set to 200."
    )
    assert res.success is True
    assert isinstance(parsed, dict)
    assert parsed.get("status") == "active"
    assert parsed.get("code") == 200

def test_api_key_never_leaked_in_errors():
    """Verify that logger outputs and error strings never expose API keys."""
    from config import GEMINI_API_KEY
    if GEMINI_API_KEY:
        fake_log = f"Connection failed to endpoint with authorization key: {GEMINI_API_KEY}"
        sanitized = AIProviderService._sanitize_log_message(fake_log)
        assert GEMINI_API_KEY not in sanitized
        assert "[REDACTED_GEMINI_KEY]" in sanitized

def test_mock_mode_for_offline_testing():
    """Verify deterministic mock mode for CI/offline environments."""
    set_mock_mode(True, {"default": '{"mocked": true, "product": "Paithani Saree"}'})
    parsed, res = AIProviderService.generate_json("Any prompt")
    assert res.success is True
    assert parsed.get("mocked") is True
    assert parsed.get("product") == "Paithani Saree"

def test_langgraph_procurement_workflow_grounded():
    """Verify that LangGraph synthesizes an executive recommendation grounded in the Firestore catalog."""
    workflow = build_workflow()
    initial_state = {
        "raw_user_request": "Source 20 units of Paithani Saree for boutique in Pune within 5 days",
        "user_id": "buyer-test-77",
        "candidate_products": [],
        "candidate_suppliers": [],
        "supplier_evaluations": [],
        "selected_supplier": None,
        "selected_product": None,
        "candidate_routes": [],
        "selected_route": None,
        "risk_analysis": None,
        "replan_count": 0,
        "max_replans": 2,
        "final_plan": None,
        "logs": [],
        "errors": []
    }

    final_state = workflow.invoke(initial_state)
    plan = final_state.get("final_plan")

    assert plan is not None
    assert plan.get("quantity") == 20
    assert plan.get("total_cost") > 0
    assert "Executive Sourcing Narrative" in plan.get("executiveSummary", "")
    assert len(final_state.get("logs", [])) >= 5

def test_langgraph_out_of_scope_query():
    """Verify that out-of-scope requests (e.g. iPhone) are cleanly rejected without hallucinating artisan items."""
    workflow = build_workflow()
    initial_state = {
        "raw_user_request": "I want to buy 10 Apple iPhones and MacBook Pros",
        "user_id": "buyer-test-88",
        "candidate_products": [],
        "candidate_suppliers": [],
        "supplier_evaluations": [],
        "selected_supplier": None,
        "selected_product": None,
        "candidate_routes": [],
        "selected_route": None,
        "risk_analysis": None,
        "replan_count": 0,
        "max_replans": 2,
        "final_plan": None,
        "logs": [],
        "errors": []
    }

    final_state = workflow.invoke(initial_state)
    plan = final_state.get("final_plan")

    assert plan is not None
    assert "Out of Scope" in plan.get("executiveSummary", "")
    assert plan.get("product_cost") == 0
