"""
BharatLink Nexus AI — Pure Python Retail & Commerce Intelligence Platform
FastAPI Application serving SSR Jinja2 templates, static assets, and REST APIs.
Features:
  - Cryptographically signed sessions & Firebase ID token verification
  - Role-Based Access Control (RBAC) & Tenant Isolation
  - Cloud Firestore unified repository with ACID inventory transactions
  - Google Gemini 2.5 Flash / 3.8 Flash & Groq multi-provider integration
  - LangGraph 6-agent procurement workflow
  - Real-time inventory intelligence, demand forecasting, & market basket analytics
  - Conversational AI Shopping Assistant & Seller Business Decision Assistant
  - Google Cloud Run production readiness (0.0.0.0:$PORT)
"""

import os
import gc
import json
import re
import socket
import logging
import markdown
from datetime import datetime
from typing import Optional, Dict, Any, List

import uvicorn
from fastapi import FastAPI, Request, Form, HTTPException, Response, Depends, status
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from config import (
    PORT,
    ENVIRONMENT,
    AI_PROVIDER,
    GEMINI_MODEL,
    GROQ_MODEL,
    ALLOW_LOCAL_FALLBACK
)
from services.repository import RepositoryService, InsufficientStockError, UnauthorizedTenantError
from services.firebase_service import FirebaseAuthService
from services.ai_provider import AIProviderService
from services.retail_intelligence import (
    RetailDiscoveryService,
    DiscoveryQuery,
    InventoryIntelligenceService,
    DemandForecastService,
    AnalyticsService,
    BusinessDecisionAssistantService
)
from agents.workflow import build_workflow
from services.route_optimizer import RouteOptimizerService
from services.auth_service import AuthService
from services.seo_service import SEOService
from services.articles_data import ARTICLES_CATALOG
from services.email_service import EmailService

logger = logging.getLogger("BharatLink.Main")

app = FastAPI(
    title="BharatLink Nexus AI — Agentic Retail & Commerce Intelligence Platform",
    version="4.0.0",
    docs_url="/api/docs" if ENVIRONMENT != "production" else None,
    redoc_url=None
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Initialize Repository Service
RepositoryService.initialize()

# Compile LangGraph Workflow
workflow_app = build_workflow()

# Custom Jinja Filter for Markdown Rendering
def format_markdown(text: str) -> str:
    if not text:
        return ""
    return markdown.markdown(text, extensions=['extra', 'nl2br', 'tables'])

templates.env.filters["markdown"] = format_markdown

# ============================================================
# PYDANTIC V2 SCHEMAS
# ============================================================
class ProcurementRequest(BaseModel):
    prompt: str = Field(..., min_length=2, max_length=1500)

class StockUpdateRequest(BaseModel):
    productId: str
    availableStock: int = Field(..., ge=0)

class OrderStatusUpdateRequest(BaseModel):
    orderId: str
    status: str

class ProductDeleteRequest(BaseModel):
    productId: str

class WhatsAppStatusRequest(BaseModel):
    resultId: Optional[str] = None
    sellerName: str
    productName: str
    status: str = "Seller Contacted"

class ContactInquiryRequest(BaseModel):
    fullName: str
    email: str
    query: str

class ChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    conversationHistory: Optional[List[Dict[str, str]]] = None

class BusinessAssistantRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=1000)

class CustomerPreferencesRequest(BaseModel):
    preferred_categories: List[str] = []
    max_budget: Optional[float] = 0.0
    preferred_region: Optional[str] = ""
    destination: Optional[str] = "India"
    consent_given: bool = True

# ============================================================
# CRYPTOGRAPHIC AUTHENTICATION & IDENTITY HELPERS
# ============================================================
def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    """
    Derives user identity from verified Firebase ID token or signed session cookie.
    Never trusts raw client-controlled unsigned JSON!
    """
    # 1. Check Authorization Bearer header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1].strip()
        decoded = FirebaseAuthService.verify_firebase_id_token(token)
        if decoded:
            return decoded

    # 2. Check signed HMAC cookie
    signed_session = request.cookies.get("buyer_session")
    if signed_session:
        user = FirebaseAuthService.verify_signed_session(signed_session)
        if user:
            return user

    return None

def get_current_seller(request: Request) -> Optional[Dict[str, Any]]:
    """Derives authenticated seller identity with verified ownership."""
    # 1. Check Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1].strip()
        decoded = FirebaseAuthService.verify_firebase_id_token(token)
        if decoded:
            seller = RepositoryService.get_seller_by_user_id(decoded.get("uid", ""))
            return {"user": decoded, "seller": seller}

    # 2. Check signed seller session cookie
    signed_seller_session = request.cookies.get("seller_session")
    if signed_seller_session:
        user = FirebaseAuthService.verify_signed_session(signed_seller_session)
        if user:
            seller = RepositoryService.get_seller_by_user_id(user.get("id") or user.get("uid"))
            return {"user": user, "seller": seller}

    # Fallback to buyer session if seller profile exists
    buyer_user = get_current_user(request)
    if buyer_user:
        seller = RepositoryService.get_seller_by_user_id(buyer_user.get("id") or buyer_user.get("uid"))
        if seller or buyer_user.get("role") == "admin":
            return {"user": buyer_user, "seller": seller}

    return None

def require_admin(request: Request) -> Dict[str, Any]:
    user = get_current_user(request)
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator privileges required.")
    return user

# ============================================================
# CLOUD RUN HEALTH & READINESS PROBES
# ============================================================
@app.get("/health", response_class=JSONResponse)
def health_liveness():
    return {
        "status": "ok",
        "service": "bharatlink-nexus-ai",
        "timestamp": datetime.utcnow().isoformat(),
        "ai_provider": AI_PROVIDER,
        "environment": ENVIRONMENT
    }

@app.get("/health/ready", response_class=JSONResponse)
def health_readiness():
    info = RepositoryService.get_connection_info()
    is_connected = info["firestore_connected"]

    fallback_explicit = os.getenv("ALLOW_LOCAL_FALLBACK", "").lower() in ("true", "1", "yes")
    # In production, Cloud Firestore connectivity is strictly required unless local fallback is explicitly allowed
    if ENVIRONMENT == "production" and not is_connected and not fallback_explicit:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "ready": False,
                "database": "cloud_firestore",
                "error": "Required Cloud Firestore dependency is unavailable",
                "environment": ENVIRONMENT,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    prods_peek = RepositoryService.get_products(limit=1)
    return {
        "status": "ready",
        "ready": True,
        "database": "cloud_firestore" if is_connected else "local_repository_fallback",
        "firestore_connected": is_connected,
        "source": info.get("source", "unknown"),
        "products_count": info.get("products_count", len(prods_peek)),
        "fallback_active": not is_connected or info.get("source") != "cloud_firestore",
        "sample_catalog_available": len(prods_peek) > 0,
        "project_id": info["project_id"],
        "environment": ENVIRONMENT,
        "timestamp": datetime.utcnow().isoformat()
    }

# ============================================================
# AUTHENTICATION ROUTES (FIREBASE & SECURE SESSIONS)
# ============================================================
@app.get("/login", response_class=HTMLResponse)
def buyer_login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html", context={})

@app.post("/login", response_class=HTMLResponse)
def buyer_login_submit(request: Request, response: Response, email: str = Form(...), password: str = Form(...)):
    res = AuthService.login_user(email, password)
    if res["success"]:
        user = res["user"]
        target = "/admin/dashboard" if user.get("role") == "admin" else "/procure"
        resp = RedirectResponse(url=target, status_code=303)
        resp.set_cookie(
            key="buyer_session",
            value=res["session_token"],
            max_age=86400,
            httponly=True,
            samesite="lax",
            secure=(ENVIRONMENT == "production")
        )
        return resp

    return templates.TemplateResponse(request=request, name="login.html", context={"error": res.get("error", "Invalid email or password.")})

@app.get("/signup", response_class=HTMLResponse)
def buyer_signup_page(request: Request):
    return templates.TemplateResponse(request=request, name="signup.html", context={})

@app.post("/signup", response_class=HTMLResponse)
def buyer_signup_submit(request: Request, full_name: str = Form(...), company_name: str = Form(""), email: str = Form(...), password: str = Form(...)):
    res = AuthService.signup_buyer(email, password, full_name, company_name)
    if res["success"]:
        resp = RedirectResponse(url="/procure", status_code=303)
        resp.set_cookie(
            key="buyer_session",
            value=res["session_token"],
            max_age=86400,
            httponly=True,
            samesite="lax",
            secure=(ENVIRONMENT == "production")
        )
        return resp

    return templates.TemplateResponse(request=request, name="signup.html", context={"error": res.get("error", "Signup failed.")})

@app.get("/logout")
def logout(response: Response):
    resp = RedirectResponse(url="/", status_code=303)
    resp.delete_cookie("buyer_session")
    resp.delete_cookie("seller_session")
    return resp

# ============================================================
# BUYER PLATFORM PUBLIC & INDEXABLE CONTENT ROUTES
# ============================================================
@app.get("/", response_class=HTMLResponse)
def page_home(request: Request):
    user = get_current_user(request)
    meta_context = SEOService.generate_meta_context(
        path="/",
        title="BharatLink Nexus AI | Agentic Retail & Commerce Intelligence Platform",
        description="Discover authentic Indian artisan products with AI-powered supplier sourcing, inventory intelligence and predictive demand analytics."
    )
    return templates.TemplateResponse(request=request, name="index.html", context={"user": user, "active_page": "home", "meta_context": meta_context})

@app.get("/how-it-works", response_class=HTMLResponse)
def page_how_it_works(request: Request):
    user = get_current_user(request)
    meta_context = SEOService.generate_meta_context(
        path="/how-it-works",
        title="How AI Procurement Works | BharatLink Nexus AI",
        description="Learn how our 6-agent LangGraph workflow evaluates Indian artisan products, verifies inventory stock, and maps transit corridors.",
        breadcrumbs=[{"name": "Home", "url": "/"}, {"name": "How It Works", "url": "/how-it-works"}]
    )
    return templates.TemplateResponse(request=request, name="how_it_works.html", context={"user": user, "active_page": "how_it_works", "meta_context": meta_context})

@app.get("/about", response_class=HTMLResponse)
def page_about(request: Request):
    user = get_current_user(request)
    meta_context = SEOService.generate_meta_context(
        path="/about",
        title="About BharatLink Nexus AI | Retail & Commerce Intelligence",
        description="Connecting global B2B procurement buyers directly with verified Indian artisan collectives through Google Gemini and Cloud Firestore.",
        breadcrumbs=[{"name": "Home", "url": "/"}, {"name": "About", "url": "/about"}]
    )
    return templates.TemplateResponse(request=request, name="about.html", context={"user": user, "active_page": "about", "meta_context": meta_context})

@app.get("/contact", response_class=HTMLResponse)
def page_contact(request: Request):
    user = get_current_user(request)
    meta_context = SEOService.generate_meta_context(
        path="/contact",
        title="Contact BharatLink Nexus AI | Buyer & Seller Inquiries",
        description="Contact our team for B2B artisan procurement assistance or Seller Central onboarding.",
        breadcrumbs=[{"name": "Home", "url": "/"}, {"name": "Contact", "url": "/contact"}]
    )
    return templates.TemplateResponse(request=request, name="contact.html", context={"user": user, "active_page": "contact", "meta_context": meta_context})

@app.post("/contact", response_class=HTMLResponse)
def submit_contact_query(request: Request, full_name: str = Form(...), email: str = Form(...), query: str = Form(...)):
    user = get_current_user(request)
    EmailService.send_contact_inquiry(full_name=full_name, sender_email=email, query_text=query)
    success_msg = f"Thank you, {full_name}! Your inquiry has been dispatched. We will contact you at {email} within 24 hours."
    return templates.TemplateResponse(request=request, name="contact.html", context={
        "user": user,
        "active_page": "contact",
        "success_msg": success_msg
    })

@app.post("/api/contact")
def api_contact_submit(req: ContactInquiryRequest):
    EmailService.send_contact_inquiry(full_name=req.fullName, sender_email=req.email, query_text=req.query)
    return {"success": True, "message": "Inquiry submitted successfully."}

@app.get("/privacy", response_class=HTMLResponse)
def page_privacy(request: Request):
    user = get_current_user(request)
    return templates.TemplateResponse(request=request, name="privacy.html", context={"user": user, "active_page": "privacy"})

@app.get("/terms", response_class=HTMLResponse)
def page_terms(request: Request):
    user = get_current_user(request)
    return templates.TemplateResponse(request=request, name="terms.html", context={"user": user, "active_page": "terms"})

@app.get("/resources", response_class=HTMLResponse)
def page_resources(request: Request):
    user = get_current_user(request)
    return templates.TemplateResponse(request=request, name="resources.html", context={"user": user, "active_page": "resources", "articles": ARTICLES_CATALOG})

@app.get("/resources/{article_slug}", response_class=HTMLResponse)
def page_resource_article(request: Request, article_slug: str):
    user = get_current_user(request)
    article = ARTICLES_CATALOG.get(article_slug)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return templates.TemplateResponse(request=request, name="resource_article.html", context={"user": user, "article": article})

@app.get("/crafts", response_class=HTMLResponse)
def page_crafts(request: Request):
    user = get_current_user(request)
    crafts = SEOService.get_craft_catalog()
    return templates.TemplateResponse(request=request, name="craft_detail.html", context={"user": user, "active_page": "crafts", "is_index": True, "crafts": crafts})

@app.get("/crafts/{craft_slug}", response_class=HTMLResponse)
def page_craft_detail(request: Request, craft_slug: str):
    user = get_current_user(request)
    crafts = SEOService.get_craft_catalog()
    craft = crafts.get(craft_slug)
    if not craft:
        raise HTTPException(status_code=404, detail="Craft category not found")

    all_products = RepositoryService.get_products()
    matching = [p for p in all_products if (craft_slug.replace('-', ' ') in p.get('category', '').lower() or craft_slug.replace('-', ' ') in p.get('name', '').lower() or craft['name'].lower() in p.get('name', '').lower())]
    return templates.TemplateResponse(request=request, name="craft_detail.html", context={"user": user, "active_page": "crafts", "is_index": False, "craft": craft, "products": matching})

@app.get("/regions", response_class=HTMLResponse)
def page_regions(request: Request):
    user = get_current_user(request)
    regions = SEOService.get_region_catalog()
    return templates.TemplateResponse(request=request, name="region_detail.html", context={"user": user, "active_page": "regions", "is_index": True, "regions": regions})

@app.get("/regions/{region_slug}", response_class=HTMLResponse)
def page_region_detail(request: Request, region_slug: str):
    user = get_current_user(request)
    regions = SEOService.get_region_catalog()
    region = regions.get(region_slug)
    if not region:
        raise HTTPException(status_code=404, detail="Regional cluster not found")
    return templates.TemplateResponse(request=request, name="region_detail.html", context={"user": user, "active_page": "regions", "is_index": False, "region": region})

@app.get("/products/{product_id}", response_class=HTMLResponse)
def page_product_detail(request: Request, product_id: str):
    user = get_current_user(request)
    product = RepositoryService.get_product_by_id(product_id)

    if not product or not product.get("active", True):
        raise HTTPException(status_code=404, detail="Product not found or unpublished")

    domain = SEOService.get_domain()
    raw_img = product.get("image_url") or ""
    img_url = raw_img if (raw_img.startswith("http") or raw_img.startswith("/static")) else f"{domain}/static/images/logo.png"

    meta_context = SEOService.generate_meta_context(
        path=f"/products/{product_id}",
        title=f"{product.get('name')} | BharatLink Nexus AI",
        description=f"Source authentic {product.get('name')} by {product.get('seller_name')}. Unit price: INR {float(product.get('price', 0)):,.2f}."
    )

    return templates.TemplateResponse(request=request, name="product_detail.html", context={"user": user, "product": product, "meta_context": meta_context})

# ============================================================
# PRIVATE BUYER USER ROUTES
# ============================================================
@app.get("/procure", response_class=HTMLResponse)
def page_procure(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse(request=request, name="procure.html", context={"user": user, "active_page": "procure"})

@app.get("/dashboard", response_class=HTMLResponse)
def page_dashboard(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    user_id = user.get("id") or user.get("uid")
    history = RepositoryService.get_procurement_history(user_id=user_id)
    products = RepositoryService.get_products(limit=10)
    sellers = RepositoryService.get_sellers(limit=6)

    return templates.TemplateResponse(request=request, name="dashboard.html", context={
        "user": user,
        "active_page": "dashboard",
        "history": history,
        "products": products,
        "sellers": sellers
    })

@app.get("/history", response_class=HTMLResponse)
def page_history(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    user_id = user.get("id") or user.get("uid")
    history = RepositoryService.get_procurement_history(user_id=user_id)
    return templates.TemplateResponse(request=request, name="history.html", context={
        "user": user,
        "active_page": "history",
        "history": history
    })

@app.get("/saved", response_class=HTMLResponse)
def page_saved(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    user_id = user.get("id") or user.get("uid")
    history = RepositoryService.get_procurement_history(user_id=user_id)
    return templates.TemplateResponse(request=request, name="saved.html", context={
        "user": user,
        "active_page": "saved",
        "history": history[:3]
    })

@app.get("/profile", response_class=HTMLResponse)
def page_profile(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    user_id = user.get("id") or user.get("uid")
    prefs = RepositoryService.get_customer_preferences(user_id) or {}
    return templates.TemplateResponse(request=request, name="profile.html", context={"user": user, "active_page": "profile", "prefs": prefs})

# ============================================================
# SELLER CENTRAL PLATFORM ROUTES (ROLE & TENANT PROTECTED)
# ============================================================
@app.get("/seller-central", response_class=HTMLResponse)
def seller_portal(request: Request):
    seller_user = get_current_seller(request)
    return templates.TemplateResponse(request=request, name="seller/portal.html", context={"seller_user": seller_user, "active_page": "portal"})

@app.get("/seller-central/login", response_class=HTMLResponse)
def seller_login_page(request: Request):
    return templates.TemplateResponse(request=request, name="seller/login.html", context={})

@app.post("/seller-central/login", response_class=HTMLResponse)
def seller_login_submit(request: Request, email: str = Form(...), password: str = Form(...)):
    res = AuthService.login_user(email, password)
    if res["success"]:
        user = res["user"]
        seller = res.get("seller")
        is_admin = (user.get("role") == "admin")

        target = "/seller-central/admin/dashboard" if is_admin else "/seller-central/dashboard"
        resp = RedirectResponse(url=target, status_code=303)
        resp.set_cookie(
            key="seller_session",
            value=res["session_token"],
            max_age=86400,
            httponly=True,
            samesite="lax",
            secure=(ENVIRONMENT == "production")
        )
        return resp

    return templates.TemplateResponse(request=request, name="seller/login.html", context={"error": res.get("error", "Seller sign in failed.")})

@app.get("/seller-central/signup", response_class=HTMLResponse)
def seller_signup_page(request: Request):
    return templates.TemplateResponse(request=request, name="seller/signup.html", context={})

@app.post("/seller-central/signup", response_class=HTMLResponse)
def seller_signup_submit(
    request: Request,
    business_name: str = Form(...),
    contact_person: str = Form(...),
    phone: str = Form(...),
    whatsapp_number: str = Form(...),
    state: str = Form(...),
    city: str = Form(...),
    craft_category: str = Form(...),
    email: str = Form(...),
    password: str = Form(...)
):
    res = AuthService.signup_seller(
        email, password, business_name, contact_person, phone, whatsapp_number, state, city, craft_category
    )
    if res["success"]:
        return templates.TemplateResponse(request=request, name="seller/signup.html", context={
            "pending_msg": res.get("message", "Registration submitted! Your seller account is pending admin approval.")
        })
    return templates.TemplateResponse(request=request, name="seller/signup.html", context={"error": res.get("error", "Registration failed.")})

@app.get("/seller-central/dashboard", response_class=HTMLResponse)
def seller_dashboard(request: Request):
    seller_user = get_current_seller(request)
    if not seller_user:
        return RedirectResponse(url="/seller-central/login", status_code=303)

    user = seller_user.get("user") or {}
    is_admin = (user.get("role") == "admin")
    seller_info = seller_user.get("seller")
    seller_id = seller_info.get("id") if seller_info else None

    if is_admin:
        products = RepositoryService.get_products()
        sellers = RepositoryService.get_sellers(active_only=False)
        analytics = AnalyticsService.get_commerce_analytics()
    else:
        products = RepositoryService.get_products(seller_id=seller_id) if seller_id else []
        sellers = RepositoryService.get_sellers()
        analytics = AnalyticsService.get_commerce_analytics(seller_id=seller_id)

    return templates.TemplateResponse(request=request, name="seller/dashboard.html", context={
        "seller_user": seller_user,
        "active_page": "dashboard",
        "products": products,
        "sellers": sellers,
        "analytics": analytics,
        "is_admin": is_admin
    })

@app.get("/seller-central/products", response_class=HTMLResponse)
def seller_products(request: Request):
    seller_user = get_current_seller(request)
    if not seller_user:
        return RedirectResponse(url="/seller-central/login", status_code=303)

    user = seller_user.get("user") or {}
    is_admin = (user.get("role") == "admin")
    seller_info = seller_user.get("seller")
    seller_id = seller_info.get("id") if seller_info else None

    products = RepositoryService.get_products() if is_admin else (RepositoryService.get_products(seller_id=seller_id) if seller_id else [])

    return templates.TemplateResponse(request=request, name="seller/products.html", context={
        "seller_user": seller_user,
        "active_page": "products",
        "products": products,
        "is_admin": is_admin
    })

@app.get("/seller-central/products/new", response_class=HTMLResponse)
def seller_product_new_page(request: Request):
    seller_user = get_current_seller(request)
    if not seller_user:
        return RedirectResponse(url="/seller-central/login", status_code=303)
    return templates.TemplateResponse(request=request, name="seller/product_new.html", context={"seller_user": seller_user, "active_page": "products"})

@app.post("/seller-central/products/new")
def seller_product_new_submit(
    request: Request,
    name: str = Form(...),
    description: str = Form(...),
    category: str = Form(...),
    region: str = Form(...),
    price: float = Form(...),
    availableStock: int = Form(...),
    weightKg: float = Form(...),
    imageUrl: str = Form("")
):
    seller_user = get_current_seller(request)
    if not seller_user:
        raise HTTPException(status_code=401, detail="Authentication required.")

    seller_info = seller_user.get("seller")
    seller_id = seller_info.get("id") if seller_info else "artisan-guild-001"
    seller_name = seller_info.get("business_name") if seller_info else "Artisan Guild"

    RepositoryService.add_product({
        "seller_id": seller_id,
        "seller_name": seller_name,
        "name": name,
        "description": description,
        "category": category,
        "region": region,
        "price": price,
        "available_stock": availableStock,
        "minimum_order_quantity": 1,
        "weight_kg": weightKg,
        "image_url": imageUrl,
        "authenticity_status": "GI Certified Authentic",
        "active": True
    }, seller_id=seller_id)

    return RedirectResponse(url="/seller-central/products", status_code=303)

@app.post("/seller-central/products/update")
def seller_product_update_submit(
    request: Request,
    productId: str = Form(...),
    name: str = Form(...),
    description: str = Form(""),
    category: str = Form(...),
    region: str = Form(""),
    price: float = Form(...),
    availableStock: int = Form(...),
    imageUrl: str = Form("")
):
    seller_user = get_current_seller(request)
    if not seller_user:
        raise HTTPException(status_code=401, detail="Authentication required.")

    user = seller_user.get("user") or {}
    is_admin = (user.get("role") == "admin")
    seller_id = seller_user.get("seller", {}).get("id") if seller_user.get("seller") else ""

    try:
        RepositoryService.update_product(
            product_id=productId,
            update_data={
                "name": name,
                "description": description,
                "category": category,
                "region": region,
                "price": price,
                "available_stock": availableStock,
                "image_url": imageUrl
            },
            actor_seller_id=seller_id,
            is_admin=is_admin
        )
    except UnauthorizedTenantError as e:
        raise HTTPException(status_code=403, detail=str(e))

    return RedirectResponse(url="/seller-central/products", status_code=303)

@app.post("/seller-central/products/delete")
def seller_product_delete_submit(request: Request, req: ProductDeleteRequest):
    seller_user = get_current_seller(request)
    if not seller_user:
        raise HTTPException(status_code=401, detail="Authentication required.")

    user = seller_user.get("user") or {}
    is_admin = (user.get("role") == "admin")
    seller_id = seller_user.get("seller", {}).get("id") if seller_user.get("seller") else ""

    try:
        success = RepositoryService.delete_product(req.productId, actor_seller_id=seller_id, is_admin=is_admin)
        return {"success": success}
    except UnauthorizedTenantError as e:
        raise HTTPException(status_code=403, detail=str(e))

@app.get("/seller-central/inventory", response_class=HTMLResponse)
def seller_inventory(request: Request):
    seller_user = get_current_seller(request)
    if not seller_user:
        return RedirectResponse(url="/seller-central/login", status_code=303)

    user = seller_user.get("user") or {}
    is_admin = (user.get("role") == "admin")
    seller_id = seller_user.get("seller", {}).get("id") if seller_user.get("seller") else None

    products = RepositoryService.get_products() if is_admin else (RepositoryService.get_products(seller_id=seller_id) if seller_id else [])
    analytics = InventoryIntelligenceService.get_inventory_health(seller_id=seller_id)

    return templates.TemplateResponse(request=request, name="seller/inventory.html", context={
        "seller_user": seller_user,
        "active_page": "inventory",
        "products": products,
        "analytics": analytics,
        "is_admin": is_admin
    })

@app.post("/seller-central/inventory/update")
def seller_inventory_update(request: Request, req: StockUpdateRequest):
    seller_user = get_current_seller(request)
    if not seller_user:
        raise HTTPException(status_code=401, detail="Authentication required.")

    user = seller_user.get("user") or {}
    is_admin = (user.get("role") == "admin")
    seller_id = seller_user.get("seller", {}).get("id") if seller_user.get("seller") else ""

    try:
        res = RepositoryService.update_product(
            product_id=req.productId,
            update_data={"available_stock": req.availableStock},
            actor_seller_id=seller_id,
            is_admin=is_admin
        )
        return {"success": True, "product": res}
    except UnauthorizedTenantError as e:
        raise HTTPException(status_code=403, detail=str(e))

@app.post("/seller-central/inventory/update-order-status")
def seller_order_status_update(request: Request, req: OrderStatusUpdateRequest):
    seller_user = get_current_seller(request)
    if not seller_user:
        raise HTTPException(status_code=401, detail="Authentication required.")

    user = seller_user.get("user") or {}
    is_admin = (user.get("role") == "admin")
    seller_id = seller_user.get("seller", {}).get("id") if seller_user.get("seller") else ""

    try:
        success = RepositoryService.update_order_status(req.orderId, req.status, actor_id=seller_id, is_admin=is_admin)
        return {"success": success, "status": req.status}
    except UnauthorizedTenantError as e:
        raise HTTPException(status_code=403, detail=str(e))

@app.get("/seller-central/analytics", response_class=HTMLResponse)
def seller_analytics(request: Request):
    seller_user = get_current_seller(request)
    if not seller_user:
        return RedirectResponse(url="/seller-central/login", status_code=303)

    user = seller_user.get("user") or {}
    is_admin = (user.get("role") == "admin")
    seller_id = seller_user.get("seller", {}).get("id") if seller_user.get("seller") else None

    analytics = AnalyticsService.get_commerce_analytics(seller_id=seller_id)
    forecast = DemandForecastService.generate_forecast(seller_id=seller_id, horizon_days=30)
    inventory = InventoryIntelligenceService.get_inventory_health(seller_id=seller_id)

    return templates.TemplateResponse(request=request, name="seller/analytics.html", context={
        "seller_user": seller_user,
        "active_page": "analytics",
        "analytics": analytics,
        "forecast": forecast,
        "inventory": inventory,
        "is_admin": is_admin
    })

@app.get("/seller-central/reviews", response_class=HTMLResponse)
def seller_reviews(request: Request):
    seller_user = get_current_seller(request)
    if not seller_user:
        return RedirectResponse(url="/seller-central/login", status_code=303)

    user = seller_user.get("user") or {}
    is_admin = (user.get("role") == "admin")
    seller_id = seller_user.get("seller", {}).get("id") if seller_user.get("seller") else None
    analytics = AnalyticsService.get_commerce_analytics(seller_id=seller_id)

    return templates.TemplateResponse(request=request, name="seller/reviews.html", context={
        "seller_user": seller_user,
        "active_page": "reviews",
        "analytics": analytics,
        "is_admin": is_admin
    })

@app.get("/seller-central/gallery", response_class=HTMLResponse)
def seller_gallery(request: Request):
    seller_user = get_current_seller(request)
    if not seller_user:
        return RedirectResponse(url="/seller-central/login", status_code=303)

    user = seller_user.get("user") or {}
    is_admin = (user.get("role") == "admin")
    seller_id = seller_user.get("seller", {}).get("id") if seller_user.get("seller") else None
    products = RepositoryService.get_products() if is_admin else (RepositoryService.get_products(seller_id=seller_id) if seller_id else [])

    return templates.TemplateResponse(request=request, name="seller/gallery.html", context={
        "seller_user": seller_user,
        "active_page": "gallery",
        "products": products,
        "is_admin": is_admin
    })

@app.get("/seller-central/tips", response_class=HTMLResponse)
def seller_tips(request: Request):
    seller_user = get_current_seller(request)
    return templates.TemplateResponse(request=request, name="seller/tips.html", context={"seller_user": seller_user, "active_page": "tips"})

@app.get("/seller-central/profile", response_class=HTMLResponse)
def seller_profile(request: Request):
    seller_user = get_current_seller(request)
    if not seller_user:
        return RedirectResponse(url="/seller-central/login", status_code=303)
    return templates.TemplateResponse(request=request, name="seller/profile.html", context={"seller_user": seller_user, "active_page": "profile"})

# ============================================================
# ADMINISTRATOR CONTROL ROUTES (RESTRICTED TO ADMINS)
# ============================================================
@app.get("/admin/dashboard", response_class=HTMLResponse)
def admin_dashboard(request: Request):
    user = get_current_user(request)
    if not user or user.get("role") != "admin":
        return RedirectResponse(url="/login", status_code=303)

    buyers = [u for u in RepositoryService._db.get("users", {}).values()]
    history = RepositoryService.get_procurement_history(limit=50)
    total_spending = sum(item.get("total_cost", 0) for item in history)

    return templates.TemplateResponse(request=request, name="admin_dashboard.html", context={
        "user": user,
        "buyers": buyers,
        "history": history,
        "total_spending": total_spending
    })

@app.get("/seller-central/admin/dashboard", response_class=HTMLResponse)
def seller_admin_dashboard(request: Request):
    seller_user = get_current_seller(request)
    user = seller_user.get("user") if seller_user else None
    if not user or user.get("role") != "admin":
        return RedirectResponse(url="/seller-central/login", status_code=303)

    sellers = RepositoryService.get_sellers(active_only=False)
    products = RepositoryService.get_products(limit=50)

    return templates.TemplateResponse(request=request, name="seller/admin_dashboard.html", context={
        "seller_user": seller_user,
        "sellers": sellers,
        "products": products
    })

@app.post("/seller-central/admin/approve")
def seller_admin_approve(request: Request, seller_id: str = Form(...)):
    user = require_admin(request)
    AuthService.approve_seller(seller_id, admin_user_id=user.get("id") or user.get("uid"))
    return RedirectResponse(url="/seller-central/admin/dashboard", status_code=303)

@app.post("/seller-central/admin/deactivate")
def seller_admin_deactivate(request: Request, seller_id: str = Form(...)):
    user = require_admin(request)
    AuthService.deactivate_seller(seller_id, admin_user_id=user.get("id") or user.get("uid"))
    return RedirectResponse(url="/seller-central/admin/dashboard", status_code=303)

# ============================================================
# RETAIL & COMMERCE INTELLIGENCE APIS
# ============================================================
@app.post("/api/procurement")
def run_procurement(request: Request, req: ProcurementRequest):
    user = get_current_user(request)
    user_id = (user.get("id") or user.get("uid")) if user else None

    initial_input = {
        "raw_user_request": req.prompt,
        "user_id": user_id,
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

    try:
        final_state = workflow_app.invoke(initial_input)
        final_plan = final_state.get("final_plan")
        if final_plan and "executiveSummary" in final_plan:
            raw_summary = final_plan["executiveSummary"]
            final_plan["executiveSummaryHtml"] = markdown.markdown(raw_summary, extensions=['extra', 'tables', 'sane_lists'])

        response_data = {
            "success": True,
            "finalPlan": final_plan,
            "logs": final_state.get("logs", []),
            "replanCount": final_state.get("replan_count", 0),
            "errors": final_state.get("errors", [])
        }

        del final_state
        del initial_input
        gc.collect()

        return response_data
    except Exception as e:
        logger.error(f"Procurement multi-agent workflow error: {e}")
        gc.collect()
        raise HTTPException(status_code=500, detail="Unable to complete procurement analysis. Please try again.")

@app.post("/api/chat")
def conversational_shopping_assistant(request: Request, chat_req: ChatMessageRequest):
    """
    Friendly Conversational Shopping Assistant powered by Google Gemini (GEMINI_API_KEY).
    Answers naturally, shares artisan heritage, and recommends grounded catalog items warmly.
    """
    user = get_current_user(request)
    user_id = (user.get("id") or user.get("uid")) if user else None

    # Clean words to check if query has specific product/craft keywords
    clean_msg = re.sub(r'[^a-zA-Z0-9\s]', ' ', chat_req.message.lower())
    raw_words = [w.strip() for w in clean_msg.split() if len(w.strip()) >= 3]
    meaningful_tokens = [
        w for w in raw_words 
        if w not in RetailDiscoveryService.STOP_WORDS 
        and w not in {"hello", "namaste", "morning", "evening", "thanks", "thank", "doing", "good", "there", "hey"}
    ]

    catalog_context = []
    recommended = []

    # Only discover products if user is actually inquiring about crafts/items
    if meaningful_tokens:
        dq = DiscoveryQuery(query_text=chat_req.message, user_id=user_id, min_stock=1)
        discovered = RetailDiscoveryService.discover_products(dq)[:4]
        for d in discovered:
            if d.match_score >= 35:
                p = d.product
                catalog_context.append({
                    "name": p["name"],
                    "seller": p.get("seller_name", "Artisan Guild"),
                    "category": p["category"],
                    "price_inr": p["price"],
                    "available_stock": p["available_stock"],
                    "region": p.get("region", "India"),
                    "authenticity": p.get("authenticity_status", "GI Certified")
                })
                recommended.append(p)

    system_prompt = (
        "You are Mira, the warm, polite, and friendly conversational shopping assistant for BharatLink Nexus AI. "
        "BharatLink Nexus AI connects global buyers directly with verified Indian artisan guilds, handloom weavers, "
        "and GI-certified traditional craft collectives.\n\n"
        "YOUR CORE GUIDELINES:\n"
        "1. Warm & Friendly Persona: Always greet visitors warmly (e.g., 'Namaste!' or 'Hello!'). Converse naturally, with genuine enthusiasm for Indian heritage arts and crafts.\n"
        "2. Normal Chatbot Experience: If the user says hello, asks how you are, inquires about GI tags, or chats casually, respond naturally and politely like a helpful concierge. Do NOT force sales pitches or dump tables.\n"
        "3. Product Discovery: When the user asks for products (e.g. Paithani sarees, pottery, brass decor, gifts), recommend 1 to 3 relevant items conversationally. Explain what makes them special (artisan story, weave/craft technique) and mention the price in ₹ (INR).\n"
        "4. DO NOT do raw B2B procurement: Do NOT output robotic LangGraph logs, ascii transit maps, or procurement comparison tables. You are a personal, friendly shopping chatbot. (If a buyer asks for bulk freight sourcing, gently mention they can also use the AI Procurement Studio at /procure).\n"
        "5. Grounding: Only recommend products provided in the catalog context. Never invent fake items or hallucinate prices."
    )

    if catalog_context:
        user_prompt = f"Available Verified Catalog Context:\n{json.dumps(catalog_context, indent=2)}\n\nVisitor Message: {chat_req.message}"
    else:
        user_prompt = f"Visitor Message: {chat_req.message}\n(No specific products found for this exact term in active catalog inventory)."

    ai_res = AIProviderService.generate(
        prompt=user_prompt,
        system_instruction=system_prompt,
        provider="gemini",
        model_name=GEMINI_MODEL,
        temperature=0.3
    )

    return {
        "reply": ai_res.content or "Namaste! I'm Mira from BharatLink. How can I help you explore authentic Indian artisan crafts today?",
        "recommended_products": recommended[:3],
        "provider": ai_res.provider,
        "model": ai_res.model
    }

@app.post("/api/business-assistant")
def business_decision_assistant(request: Request, b_req: BusinessAssistantRequest):
    seller_user = get_current_seller(request)
    seller_id = seller_user.get("seller", {}).get("id") if seller_user and seller_user.get("seller") else None

    res = BusinessDecisionAssistantService.answer_business_query(
        question=b_req.question,
        seller_id=seller_id
    )
    return res

@app.get("/api/preferences")
def get_user_preferences(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required.")
    user_id = user.get("id") or user.get("uid")
    prefs = RepositoryService.get_customer_preferences(user_id) or {}
    return {"preferences": prefs}

@app.post("/api/preferences")
def save_user_preferences(request: Request, p_req: CustomerPreferencesRequest):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required.")
    user_id = user.get("id") or user.get("uid")
    updated = RepositoryService.save_customer_preferences(user_id, p_req.dict())
    return {"success": True, "preferences": updated}

@app.delete("/api/preferences")
def delete_user_preferences(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required.")
    user_id = user.get("id") or user.get("uid")
    success = RepositoryService.delete_customer_preferences(user_id)
    return {"success": success}

@app.get("/api/retail/inventory-health")
def api_inventory_health(request: Request):
    seller_user = get_current_seller(request)
    seller_id = seller_user.get("seller", {}).get("id") if seller_user and seller_user.get("seller") else None
    return InventoryIntelligenceService.get_inventory_health(seller_id=seller_id)

@app.get("/api/retail/demand-forecast")
def api_demand_forecast(request: Request, horizon_days: int = 30):
    seller_user = get_current_seller(request)
    seller_id = seller_user.get("seller", {}).get("id") if seller_user and seller_user.get("seller") else None
    return DemandForecastService.generate_forecast(seller_id=seller_id, horizon_days=horizon_days)

@app.get("/api/retail/basket-analysis")
def api_basket_analysis(request: Request):
    seller_user = get_current_seller(request)
    seller_id = seller_user.get("seller", {}).get("id") if seller_user and seller_user.get("seller") else None
    return AnalyticsService.get_commerce_analytics(seller_id=seller_id)

@app.get("/api/history")
def get_history(request: Request):
    user = get_current_user(request)
    user_id = (user.get("id") or user.get("uid")) if user else None
    return {"history": RepositoryService.get_procurement_history(user_id=user_id)}

@app.post("/api/procurement/whatsapp")
def track_whatsapp_contact(req: WhatsAppStatusRequest):
    return {"success": True, "status": req.status, "message": "Procurement status updated: Seller Contacted via WhatsApp"}

# SEO sitemap and robots
@app.get("/robots.txt", response_class=PlainTextResponse)
def robots_txt():
    domain = SEOService.get_domain()
    content = f"""User-agent: *\nAllow: /\nAllow: /procure\nAllow: /how-it-works\nAllow: /crafts\nAllow: /regions\nAllow: /resources\nDisallow: /admin/\nDisallow: /seller-central/admin/\nSitemap: {domain}/sitemap.xml\n"""
    return PlainTextResponse(content=content, media_type="text/plain")

@app.get("/sitemap.xml", response_class=Response)
def sitemap_xml():
    domain = SEOService.get_domain()
    xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n  <url><loc>{domain}/</loc><priority>1.0</priority></url>\n  <url><loc>{domain}/procure</loc><priority>0.9</priority></url>\n  <url><loc>{domain}/crafts</loc><priority>0.8</priority></url>\n</urlset>"""
    return Response(content=xml_content, media_type="application/xml")

# ============================================================
# PRODUCTION ASGI SERVER ENTRYPOINT (CLOUD RUN BINDING)
# ============================================================
if __name__ == "__main__":
    bind_port = int(os.getenv("PORT", 8080))
    print(f"Starting BharatLink Nexus AI on 0.0.0.0:{bind_port} ({ENVIRONMENT})")
    uvicorn.run("main:app", host="0.0.0.0", port=bind_port, reload=False)
