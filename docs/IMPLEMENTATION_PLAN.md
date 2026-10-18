# BharatLink Nexus AI — Google AI Builder Cup Implementation Plan

## 1. Executive Summary & Problem Alignment
**Project**: BharatLink Nexus AI — Agentic Retail & Commerce Intelligence Platform  
**Challenge Theme**: Retail & Commerce: Intelligent Customer and Business Experiences  
**Goal**: Transform BharatLink Nexus AI from a basic artisan sourcing prototype into a production-grade, highly secure, agentic retail & commerce intelligence platform powered by **Google Gemini (gemini-2.5-flash)** on Vertex AI / Google Gen AI SDK, **Cloud Firestore & Firebase Authentication**, and containerized for **Google Cloud Run**.

The platform preserves and champions the unique identity of 444+ GI-certified Indian artisan collectives and suppliers, while extending capabilities across modern retail commerce:
- **Buyer Experience**: Conversational shopping assistant, intelligent product discovery, deterministic inventory validation, personalized recommendations, and logistics corridor assessment.
- **Seller & Retailer Experience**: Real-time inventory intelligence, overselling prevention, audit logging, demand forecasting, customer basket analysis, and a grounded Business Decision Assistant.
- **Platform Integrity**: Zero trust identity verification via Firebase Auth, role-based access control (RBAC), tenant isolation, deterministic pricing calculations, and production Cloud Run readiness.

---

## 2. Repository Audit & Findings

### 2.1 Existing Architecture
- **Framework**: FastAPI (Python 3.10+) serving HTML via Jinja2 templates and REST/JSON endpoints.
- **Orchestration**: LangGraph 6-agent sequential graph in `agents/workflow.py`.
- **Database**: Supabase client (`services/supabase_service.py`), raw SQL migrations in `supabase/migrations/`.
- **LLM Layer**: Hardcoded Groq client calling `openai/gpt-oss-20b` in `agents/workflow.py` and `services/supabase_service.py`. No native Gemini integration yet, though `GEMINI_API_KEY` was supplied in `.env`.
- **Authentication**: Unsigned, client-controlled JSON cookies (`buyer_session`, `seller_session`).
- **Tests**: Zero automated unit/integration tests existed in the workspace.

### 2.2 Security Vulnerabilities & Remediation Matrix
| ID | Vulnerability | Severity | Remediation |
|---|---|---|---|
| **SEC-01** | Client-forgeable unsigned JSON session cookies (`buyer_session`, `seller_session`) | Critical | Replace with signed sessions / Firebase Auth ID token verification via Firebase Admin SDK. Enforce verified claims on all protected routes. |
| **SEC-02** | Hardcoded admin credentials (`admin@bharatlink.com` / `Admin@123`) & fallback bypass | Critical | Eliminate hardcoded credentials and backdoor logic. Implement secure administrative claim provisioning via Firebase Admin. |
| **SEC-03** | Unrestricted Supabase RLS (`USING (true) WITH CHECK (true)`) | High | Migrate to Cloud Firestore with strict Firestore Security Rules (`firestore.rules`) enforcing tenant isolation and least privilege. |
| **SEC-04** | Broken Tenant Isolation on Seller Endpoints (Stock, Product Updates, Orders) | Critical | Enforce backend seller ownership checks on every mutation. Validate that `seller_id` on the product matches authenticated seller's ID. |
| **SEC-05** | Lack of Input Validation & Leaking Internal Exceptions | Medium | Implement Pydantic V2 schemas for all request payloads. Mask raw server error traces with structured error responses. |
| **SEC-06** | Hardcoded External LLM Model Assumptions (`openai/gpt-oss-20b`) | Medium | Centralize model abstraction (`services/ai_provider.py`) with Google Gen AI SDK (`gemini-2.5-flash`), Vertex AI support, and configurable Groq fallback. |

---

## 3. Architecture & Data Migration to Firebase

### 3.1 Database Abstraction Layer
Create a modular repository layer (`services/firebase_service.py` & `services/repository.py`) supporting:
- **Cloud Firestore** for document storage with transactions for inventory safety.
- **Firebase Auth** via Firebase Admin SDK (`firebase_admin.auth`) for token verification.
- **Firebase Emulator & In-Memory Fallback** for local developer workflows and CI test execution without requiring cloud credentials.

### 3.2 Target Firestore Collections Schema
1. `users`: `{ uid, email, displayName, role ('buyer'|'seller'|'admin'), companyName, createdAt, updatedAt }`
2. `seller_profiles`: `{ id, userId, businessName, contactPerson, email, phone, whatsappNumber, state, city, craftCategory, verificationStatus, active, createdAt }`
3. `products`: `{ id, sellerId, sellerName, name, description, category, subcategory, region, price, availableStock, minimumOrderQuantity, weightKg, authenticityStatus, imageUrl, active, createdAt, updatedAt }`
4. `inventory_movements`: `{ id, productId, sellerId, previousStock, newStock, delta, reason, createdBy, createdAt }`
5. `procurement_requests`: `{ id, userId, rawPrompt, productType, quantity, destination, deadlineDays, budgetInr, status, createdAt }`
6. `recommendations`: `{ id, requestId, userId, supplierName, productName, quantity, productCost, shippingCost, totalCost, deliveryDays, riskLevel, routeDetails, alternatives, createdAt }`
7. `orders`: `{ id, requestId, buyerId, sellerId, productId, quantity, totalCost, status ('Pending'|'Confirmed'|'Stock Delivered'|'Cancelled'), createdAt, updatedAt }`
8. `sales_transactions`: `{ id, orderId, productId, sellerId, buyerId, unitsSold, unitPrice, totalAmount, category, timestamp }`
9. `customer_preferences`: `{ userId, preferredCategories, maxBudget, destination, sustainabilityFocus, consentGiven, updatedAt }`
10. `analytics_events`: `{ id, eventType, entityId, metadata, timestamp }`
11. `audit_logs`: `{ id, action, userId, role, ipAddress, resource, timestamp, details }`

### 3.3 Data Migration Script
- Provide `scripts/migrate_to_firestore.py` with:
  - `--dry-run` flag to validate existing SQL seed / Supabase items before committing.
  - Data sanitization, type coercion, and deduplication.
  - Comprehensive migration validation reporting.

---

## 4. Google GenAI & Multi-Provider AI Architecture

### 4.1 Centralized AI Provider (`services/ai_provider.py`)
- Official Google Gen AI SDK (`google.genai`).
- Default model: `gemini-2.5-flash` (configurable via `GEMINI_MODEL`).
- Support both:
  1. **Gemini Developer API Key**: `GEMINI_API_KEY`
  2. **Vertex AI Mode**: `GOOGLE_GENAI_USE_VERTEXAI=true`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`.
- **Secondary Provider**: Groq (`GROQ_API_KEY`, `GROQ_MODEL`) retained for specialized fallback.
- **Resilience**:
  - Configurable timeouts (default 10s).
  - Exponential backoff for transient rate limits.
  - Structured JSON validation and schema enforcement.
  - Strict grounding: No model hallucination of prices, stock, or contact numbers.
  - Tracking of model & provider without printing credentials.

---

## 5. LangGraph Multi-Agent Workflow Refactoring
Enhance `agents/workflow.py` with typed states and deterministic guardrails:
1. **Buyer Intent Agent**: Extracts structured shopping/procurement requirements (category, item, quantity, destination, budget, timeline).
2. **Product & Supplier Discovery Agent**: Retrieves grounded items from Firestore catalog using keyword/category matching.
3. **Procurement Evaluation Agent**: Compares candidate artisan sellers, verifies stock eligibility, sorts by price/feasibility.
4. **Logistics Analysis Agent**: Generates ASCII transit corridor route map with transit estimations.
5. **Risk Assessment Agent**: Checks live weather conditions via Open-Meteo API for origin & destination hubs.
6. **Decision & Explanation Agent**: Synthesizes the verified executive sourcing recommendation.

---

## 6. Retail & Commerce Intelligence Services
- **Feature A: Intelligent Product Discovery** (`services/retail_intelligence.py`):
  Semantic search, attribute matching, and explainable ranking.
- **Feature B: Personalization**:
  Consent-driven buyer preferences, category affinities, and preference management controls.
- **Feature C: Inventory Intelligence**:
  Low-stock indicators, oversell prevention with transactional checks, replenishment alert engine.
- **Feature D: Demand Forecasting**:
  Honest baseline forecasting (Moving Average & Exponential Smoothing) based on real transaction data, with explicit confidence warnings on sparse histories.
- **Feature E: Customer & Product Analytics**:
  Bestsellers, category share, and basket analysis (co-purchase support) calculated from actual records.
- **Feature F: Business Decision Assistant**:
  Seller-facing conversational assistant querying real inventory, sales, and catalog metrics without hallucinating data.

---

## 7. Automated Test Suite (`tests/`)
Build a complete test suite with `pytest`:
1. `tests/test_security.py`: Token verification, role-based access, tenant isolation, unauthorized rejections.
2. `tests/test_database.py`: Firestore repository operations, transactional stock updates, overselling protection.
3. `tests/test_ai_provider.py`: Gemini & Groq invocation, mocked outputs, timeout handling, structured JSON parsing.
4. `tests/test_retail_intelligence.py`: Discovery, personalization, inventory alerts, demand forecasting, basket analysis.
5. `tests/test_deployment.py`: `/health`, `/health/ready`, environment binding, startup validation.

---

## 8. Google Cloud Run Deployment
- **Containerization**: Multi-stage production `Dockerfile` with Python 3.10-slim.
- **Port & Host**: Bind to `0.0.0.0`, listen on `$PORT` (default 8080).
- **Asset Serving**: Package static assets and templates into the container; zero local filesystem dependencies.
- **Cloud Build**: `cloudbuild.yaml` for continuous deployment directly from GitHub repository.
- **Secret Management**: Google Cloud Secret Manager integration and Application Default Credentials (ADC).
