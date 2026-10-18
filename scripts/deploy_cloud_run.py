"""
Deployment script for BharatLink Nexus AI on Google Cloud Run.
Reads API keys safely from local environment and deploys with optimal configurations.
"""

import os
import sys
import subprocess
from dotenv import load_dotenv

load_dotenv(".env")
load_dotenv(".env.local")

groq_key = os.getenv("GROQ_API_KEY", "")
gemini_key = os.getenv("GEMINI_API_KEY", "")

if not groq_key or not gemini_key:
    print("Error: Missing GROQ_API_KEY or GEMINI_API_KEY in environment.")
    sys.exit(1)

env_vars = [
    "ENVIRONMENT=production",
    "FIREBASE_PROJECT_ID=bharatlink-nexus-ai",
    "GOOGLE_CLOUD_PROJECT=bharatlink-nexus-ai",
    "GOOGLE_CLOUD_LOCATION=asia-south1",
    "AI_PROVIDER=groq",
    "GROQ_MODEL=openai/gpt-oss-20b",
    "GROQ_PROCUREMENT_MODEL=openai/gpt-oss-20b",
    "GEMINI_MODEL=gemini-3.5-flash",
    f"GROQ_API_KEY={groq_key}",
    f"GEMINI_API_KEY={gemini_key}",
    "ALLOW_LOCAL_FALLBACK=false"
]

env_arg = ",".join(env_vars)

cmd = [
    "gcloud", "run", "deploy", "bharatlink-nexus-ai",
    "--source", ".",
    "--region", "asia-south1",
    "--project", "bharatlink-nexus-ai",
    "--allow-unauthenticated",
    "--memory", "1Gi",
    "--cpu", "1",
    "--timeout", "300",
    "--set-env-vars", env_arg
]

print("Initiating Google Cloud Run build & deployment...")
res = subprocess.run(cmd, shell=True)
sys.exit(res.returncode)
