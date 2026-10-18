# 🛍️ BharatLink Nexus AI — Autonomous B2B Artisan Sourcing & Intelligent Craft Logistics Platform

[![Google Cloud Run](https://img.shields.io/badge/Google%20Cloud%20Run-Deployed-4285F4?logo=googlecloud&logoColor=white)](https://bharatlink-nexus-ai-360360473676.asia-south1.run.app)
[![Google Cloud Firestore](https://img.shields.io/badge/Cloud%20Firestore-Connected-FFA000?logo=firebase&logoColor=white)](https://firebase.google.com/docs/firestore)
[![Google Gemini](https://img.shields.io/badge/Google%20Gemini-3.5%20Flash-8E75C2?logo=google&logoColor=white)](https://ai.google.dev/)
[![Groq](https://img.shields.io/badge/Groq-openai%2Fgpt--oss--20b-F55036?logo=groq&logoColor=white)](https://groq.com/)
[![Tests](https://img.shields.io/badge/Tests-44%20Passed%20(100%25)-brightgreen)](file:///d:/BharatLink%20Nexus%20AI%20-%20Copy/tests)

**BharatLink Nexus AI** is an AI-native B2B e-commerce procurement and multi-modal logistics intelligence platform designed to connect authentic Indian Geographical Indication (GI) certified artisan clusters, handloom cooperatives, and master craftsmen directly with institutional enterprise buyers, retail conglomerates, and global brands.

---

## 📌 Problem Statement & Solution

### The Challenge
India possesses over 3,000 unique traditional craft clusters and hundreds of GI-certified art forms, yet traditional artisan supply chains suffer from:
1. **Severe Intermediation**: Multi-layered middlemen capture up to 70% of product margins, depriving rural artisans of fair livelihoods.
2. **Fragmented Sourcing**: Institutional purchasers struggle with inconsistent lead times, unverified authenticity, and opaque pricing.
3. **Logistics & Climate Vulnerability**: Rural transit corridors are susceptible to monsoon disruptions, seasonal weather shocks, and unoptimized multi-modal freight costs.

### The BharatLink Solution
BharatLink Nexus AI unifies:
- **Autonomous Multi-Agent Procurement**: Evaluates product authenticity, negotiates wholesale pricing, and models freight routes.
- **Dedicated Dual-AI Architecture**: Employs **Groq (`openai/gpt-oss-20b`)** for sub-second 6-node LangGraph autonomous procurement, paired with **Google Gemini (`gemini-3.5-flash`)** powering "Mira", a warm and culturally grounded conversational shopping assistant.
- **Enterprise Cloud Infrastructure**: Fully containerized and deployed on **Google Cloud Run** with persistent ACID-compliant transactional inventory on **Google Cloud Firestore**.

---

## 🌟 Key Features

### 1. 🤖 6-Agent LangGraph Procurement Engine (Powered by Groq `openai/gpt-oss-20b`)
- **Buyer Intent Agent**: Extracts product specifications, required quantities, target delivery dates, and budget parameters from unstructured conversational prompts.
- **Artisan Discovery Agent**: Performs exact token and regional boundary matching against authenticated GI-certified artisan inventory.
- **Procurement Evaluation Agent**: Compares supplier quality ratings, verification tiers, stock readiness, and tier-volume wholesale pricing.
- **Logistics Optimization Agent**: Models route corridors, transit distances (km), freight mode allocations, and real-time fuel and toll costs.
- **Risk & Disruption Agent**: Proactively analyzes seasonal weather and transit disruption risks across transit hubs.
- **Decision & Synthesis Agent**: Formulates comprehensive executive procurement proposals with automated PDF generation and direct WhatsApp artisan procurement links.

### 2. 💬 Conversational Shopping Assistant — "Mira" (Powered by Google Gemini)
- Culturally attuned, conversational shopping companion helping buyers discover traditional craft heritage.
- Seamlessly suggests authentic craft pieces, weaving histories, and regional provenance without dumping overwhelming procurement logs.

### 3. 🏬 Multi-Tenant Seller Central & Admin Verification
- **Artisan Tenant Isolation**: Each artisan guild or seller maintains isolated product catalogs, stock tiers, and order tracking.
- **Admin Verification Workflow**: Platform administrators review and approve artisan sellers before catalog listings go live.
- **Cryptographically Signed HMAC Sessions**: Tamper-proof session cookies (`HttpOnly`, `SameSite=Lax`, `Secure`) with embedded expiration protection against replay attacks.

### 4. 📈 Retail & Commerce Intelligence
- **Inventory Health & Reorder Risk**: Real-time turnover analytics and stock-out alerts.
- **Demand Forecasting**: Category-level seasonal demand projections based on festival cycles and purchasing patterns.
- **Market Basket Analysis**: Uncovers cross-craft purchasing affinities and bundling opportunities.

### 5. 🔍 Production-Grade Technical SEO & PWA
- Dynamic XML sitemap (`/sitemap.xml`) indexing crafts, regional clusters, and product pages.
- Strict search engine policy via `/robots.txt` protecting authenticated and administrative routes.
- Offline-ready Progressive Web App (PWA) manifest with mobile-optimized layout.

---

## 🏗️ System Architecture

```mermaid
graph TD
    Buyer[Enterprise Buyer / User] -->|HTTPS| CloudRun[Google Cloud Run Container]
    
    subgraph BharatLink Core Platform [FastAPI Application]
        Auth[Auth Service & HMAC Sessions]
        Repo[Unified Repository Service]
        ChatAPI["/api/chat (Shopping Guide)"]
        ProcureAPI["/api/procurement (Studio)"]
        RetailAPI["/api/retail/* (Intelligence)"]
    end
    
    CloudRun --> BharatLink Core Platform
    
    subgraph Data & Storage Tier
        Firestore[(Google Cloud Firestore)]
        SeedData[(Sanitized Fallback Catalog)]
    end
    
    subgraph AI Provider Tier
        Gemini[Google Gemini 3.5 Flash]
        Groq[Groq openai/gpt-oss-20b]
    end
    
    ChatAPI -->|Prompt & Context| Gemini
    ProcureAPI -->|6-Node LangGraph| Groq
    Repo -->|Stream & ACID Transactions| Firestore
    Repo -.->|Local Dev Fallback| SeedData
```

---

## 📂 Project Directory Structure

```text
BharatLink-Nexus-AI/
├── .dockerignore                # Production Docker build exclusions
├── .env.example                 # Sanitized environment variable template
├── .gitignore                   # Comprehensive secret, dump, and cache exclusions
├── Dockerfile                   # Cloud Run optimized multi-stage container build
├── Procfile                     # Web process definition
├── README.md                    # Project documentation
├── cloudbuild.yaml              # Google Cloud Build automated deployment pipeline
├── config.py                    # Environment configuration & model settings
├── conftest.py                  # Pytest fixtures and test initialization
├── data/
│   └── catalog_seed.json        # Sanitized local fallback catalog (516 products)
├── docs/                        # Architecture, security audit, and migration docs
├── firestore.indexes.json       # Cloud Firestore compound query index specs
├── firestore.rules              # Granular Firestore security and access rules
├── main.py                      # FastAPI application entry point & 67 registered routes
├── requirements.txt             # Locked Python runtime dependencies
├── scripts/
│   ├── deploy_cloud_run.py      # Cloud Run packaging & automated deployment script
│   └── migrate_supabase_to_firestore.py  # Supabase backup parser & Firestore importer
├── services/
│   ├── ai_provider.py           # Unified Google GenAI & Groq SDK connector
│   ├── auth_service.py          # Identity, PBKDF2 hashing, and RBAC service
│   ├── firebase_service.py      # Firebase Admin SDK & HMAC-SHA256 session service
│   ├── repository.py            # Firestore persistence layer & transactional inventory
│   ├── retail_intelligence.py   # Product discovery, forecasting & basket analysis
│   ├── route_optimizer.py       # Distance, route corridor, and freight calculators
│   └── seo_service.py           # Canonical sitemap, robots.txt, and metadata engine
├── static/                      # CSS, JavaScript, icons, and static assets
├── templates/                   # SSR Jinja2 templates (buyer portal & seller central)
└── tests/                       # 44 automated unit, integration, and security tests
```

---

## ⚙️ Environment Configuration

Copy `.env.example` to `.env` and configure your credentials:

```bash
cp .env.example .env
```

| Variable | Description | Default / Example |
| :--- | :--- | :--- |
| `ENVIRONMENT` | Runtime mode (`development` or `production`) | `development` |
| `PORT` | Web server port | `8080` |
| `SECRET_KEY` | Cryptographic key for HMAC session signing | *Random 64-char string* |
| `GEMINI_API_KEY` | Google AI Studio API key for Gemini | `AIzaSy...` |
| `GEMINI_MODEL` | Gemini model for conversational shopping assistant | `gemini-3.5-flash` |
| `GROQ_API_KEY` | Groq API key for autonomous procurement engine | `gsk_...` |
| `GROQ_MODEL` | Groq model identifier | `openai/gpt-oss-20b` |
| `FIREBASE_PROJECT_ID` | Google Cloud / Firebase project identifier | `bharatlink-nexus-ai` |
| `ALLOW_LOCAL_FALLBACK` | Allow local seed catalog when Firestore is unreachable | `true` (dev) / `false` (prod) |

---

## 🚀 Local Setup & Installation

### 1. Prerequisites
- Python 3.10 or higher
- Google Cloud CLI (`gcloud`) authenticated with target project

### 2. Setup Virtual Environment
```bash
# Clone the repository
git clone https://github.com/shravanshidruk16/Bharat-Link-Nexus-AI.git
cd Bharat-Link-Nexus-AI

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Run the Development Server
```bash
python main.py
```
The application will start at `http://127.0.0.1:8080`.

---

## 🧪 Automated Testing Suite

The repository contains 44 automated tests covering AI providers, transactional inventory decrement, tenant isolation, Firestore connectivity, and security defenses:

```bash
pytest tests/ -v
```

### Test Coverage Highlights:
- **Security & Authorization (`tests/test_security.py`)**: Validates unauthenticated redirects, forged session rejection, expired token rejection, cross-tenant modification prevention, and RBAC admin protection.
- **Database & ACID Transactions (`tests/test_database.py`)**: Tests transactional inventory decrements, overselling prevention under load, and inventory audit trails.
- **AI Integration (`tests/test_ai_provider.py`)**: Tests Google Gemini generation, Groq LangGraph agent workflow, deterministic test mocks, and secret masking in log outputs.
- **Firestore Connectivity (`tests/test_firestore_connectivity.py`)**: Tests readiness probes, read-only safety, and production fallback guards.

---

## ☁️ Deployment on Google Cloud Run

The application is containerized and deployed using Google Cloud Run:

```bash
# Build and deploy directly to Cloud Run
gcloud run deploy bharatlink-nexus-ai \
    --source . \
    --region asia-south1 \
    --platform managed \
    --allow-unauthenticated \
    --set-env-vars ENVIRONMENT=production,PORT=8080,FIREBASE_PROJECT_ID=bharatlink-nexus-ai
```

### Deployment Configuration Highlights:
- **Port Binding**: Automatically binds to `0.0.0.0:$PORT` via Uvicorn.
- **Authentication**: Uses Google Cloud Application Default Credentials (ADC) attached to the runtime service account to securely interact with Cloud Firestore without storing service account keys in the container.
- **Health Checks**: Uses `/health` for liveness and `/health/ready` for traffic readiness.

---

## 🛡️ Security & Responsible Disclosure

- **Zero Hardcoded Secrets**: All credentials are read from environment variables or Google Secret Manager.
- **Tamper-Proof Sessions**: Sessions are cryptographically signed with HMAC-SHA256 and include cryptographic expiration (`exp`) timestamps.
- **Anti-XSS Defense**: Client-side Markdown parser pre-escapes HTML entities (`&`, `<`, `>`, `"`, `'`) before converting markdown formatting to prevent DOM-based script injection.
- **Tenant Isolation**: Strict cross-tenant ownership checks prevent sellers from updating or deleting other sellers' catalog listings.

For responsible vulnerability disclosure, please open a confidential security advisory on GitHub or contact the maintainers.

---

## 📜 License

Distributed under the MIT License. See [LICENSE](LICENSE) for details.  
Copyright © 2026 BharatLink Nexus AI.
