# BharatLink Nexus AI — Google Gemini & AI Provider Integration

## 1. AI Architecture Overview

BharatLink Nexus AI leverages **Google Gemini (gemini-2.5-flash)** as its primary intelligence engine for intent extraction, natural language product discovery, recommendation synthesis, and business decision support.

The integration is implemented through a centralized, provider-aware module: `services/ai_provider.py`.

### Key Capabilities:
- **Official Google Gen AI SDK**: Uses `google.genai` Client interface for modern, low-latency inferencing.
- **Configurable Model**: Initialized with `gemini-2.5-flash`, overrideable dynamically via `GEMINI_MODEL`.
- **Dual API Modes**:
  1. **Developer API Mode**: Directly utilizes `GEMINI_API_KEY` for local development or API-key based access.
  2. **Vertex AI Mode**: Automatically enabled when `GOOGLE_GENAI_USE_VERTEXAI=true` or when running on Google Cloud with ADC, utilizing project ID and location (`us-central1`).
- **Secondary Provider (Groq)**: Retains `GROQ_API_KEY` and `GROQ_MODEL` as an explicitly configured alternative provider.
- **Provider Transparency**: Tracks which provider and model executed each operation without exposing secrets or private customer prompts in logs.
- **Deterministic Guardrails**: Pricing, inventory validation, eligibility, and risk scoring are computed strictly using deterministic business logic. Gemini is used for language understanding and explainability, preventing hallucinations.

---

## 2. Configuration Parameters

Configure AI providers via environment variables:

```bash
# ============================================================
# PRIMARY: GOOGLE GEMINI CONFIGURATION
# ============================================================
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
AI_PROVIDER=gemini # 'gemini' (default) or 'groq'

# Optional Vertex AI Enterprise Configuration
GOOGLE_GENAI_USE_VERTEXAI=false # Set to true to route via Vertex AI
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=us-central1

# ============================================================
# SECONDARY: GROQ CONFIGURATION (OPTIONAL / SPECIALIZED)
# ============================================================
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile # or custom Groq model
```

---

## 3. Resilience, Timeouts & Error Handling

`services/ai_provider.py` incorporates robust enterprise-grade safeguards:
1. **Request Timeouts**: Defaults to 12 seconds per LLM call to prevent hung requests.
2. **Safe Retries**: Uses exponential backoff (up to 2 retries) exclusively for transient network errors (HTTP 429 rate limit or 503 service unavailable). Non-idempotent operations are never blindly retried.
3. **Structured Output Validation**: Utilizes JSON regex parsers and Pydantic validation to ensure model outputs strictly conform to required schemas.
4. **Mock Mode for Unit Tests**: Built-in test mock harness allowing offline testing without consuming API quota.
