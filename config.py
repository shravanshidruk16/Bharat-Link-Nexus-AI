import os
from dotenv import load_dotenv

load_dotenv(".env")
load_dotenv(".env.local")

# ============================================================
# RUNTIME & ENVIRONMENT CONFIGURATION
# ============================================================
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
PORT = int(os.getenv("PORT", 8080))
SECRET_KEY = os.getenv("SECRET_KEY", "bharatlink-nexus-ai-secure-hmac-key-2026")

# ============================================================
# PRIMARY AI PROVIDER: GOOGLE GEMINI (CONVERSATIONAL ASSISTANT & INTELLIGENCE)
# ============================================================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini").lower().strip()

# Vertex AI Settings (when GOOGLE_GENAI_USE_VERTEXAI=true or on Cloud Run ADC)
GOOGLE_GENAI_USE_VERTEXAI = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "false").lower() in ("true", "1", "yes")
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", os.getenv("GCP_PROJECT", ""))
GOOGLE_CLOUD_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

# ============================================================
# PRIMARY PROCUREMENT AI PROVIDER: GROQ (OPENAI-GPT-OSS-20B)
# ============================================================
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_API_KEY_2 = os.getenv("GROQ_API_KEY_2", os.getenv("GROQ_API_KEY", ""))
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
GROQ_PROCUREMENT_MODEL = os.getenv("GROQ_PROCUREMENT_MODEL", "openai/gpt-oss-20b")

# ============================================================
# PRIMARY DATABASE & AUTH: FIREBASE & CLOUD FIRESTORE
# ============================================================
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", GOOGLE_CLOUD_PROJECT or "bharatlink-nexus-ai")
FIREBASE_AUTH_EMULATOR_HOST = os.getenv("FIREBASE_AUTH_EMULATOR_HOST", "")
FIRESTORE_EMULATOR_HOST = os.getenv("FIRESTORE_EMULATOR_HOST", "")
ALLOW_LOCAL_FALLBACK = os.getenv(
    "ALLOW_LOCAL_FALLBACK",
    "true" if ENVIRONMENT in ("development", "test") else "false"
).lower() in ("true", "1", "yes")

# ============================================================
# LEGACY SUPABASE (RETAINED FOR NON-DESTRUCTIVE MIGRATION)
# ============================================================
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""))

