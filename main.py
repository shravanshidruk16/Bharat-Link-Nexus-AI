import os
import uvicorn
import socket
import json
import gc
import markdown
from fastapi import FastAPI, Request, Form, HTTPException, Cookie, Response
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from agents.workflow import build_workflow
from services.supabase_service import DatabaseService
from services.route_optimizer import RouteOptimizerService
from services.auth_service import AuthService
from services.seo_service import SEOService
from services.articles_data import ARTICLES_CATALOG
from services.email_service import EmailService

app = FastAPI(title="BharatLink Nexus AI — Pure Python Platform", version="3.0.0")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

workflow_app = build_workflow()

class ProcurementRequest(BaseModel):
    prompt: str

class StockUpdateRequest(BaseModel):
    productId: str
    availableStock: int

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

# Session Helper Functions using Cookies
def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    session_raw = request.cookies.get("buyer_session")
    if session_raw:
        try:
            return json.loads(session_raw)
        except Exception:
            pass
    return None

def get_current_seller(request: Request) -> Optional[Dict[str, Any]]:
    session_raw = request.cookies.get("seller_session")
    if session_raw:
        try:
            return json.loads(session_raw)
        except Exception:
            pass
    return None

# Custom Jinja Filter for Markdown Rendering
def format_markdown(text: str) -> str:
    if not text:
        return ""
    return markdown.markdown(text, extensions=['extra', 'nl2br'])

templates.env.filters["markdown"] = format_markdown

# ============================================================
# UNIFIED SMART AUTHENTICATION & ROUTING
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
        resp.set_cookie(key="buyer_session", value=json.dumps(user), max_age=86400)
        return resp

    return templates.TemplateResponse(request=request, name="login.html", context={"error": res.get("error", "Invalid email or password")})

@app.get("/signup", response_class=HTMLResponse)
def buyer_signup_page(request: Request):
    return templates.TemplateResponse(request=request, name="signup.html", context={})

@app.post("/signup", response_class=HTMLResponse)
def buyer_signup_submit(request: Request, full_name: str = Form(...), company_name: str = Form(""), email: str = Form(...), password: str = Form(...)):
    res = AuthService.signup_buyer(email, password, full_name, company_name)
    if res["success"]:
        resp = RedirectResponse(url="/procure", status_code=303)
        resp.set_cookie(key="buyer_session", value=json.dumps(res["user"]), max_age=86400)
        return resp

    return templates.TemplateResponse(request=request, name="signup.html", context={"error": res.get("error", "Signup failed")})

@app.get("/logout")
def logout(response: Response):
    resp = RedirectResponse(url="/", status_code=303)
    resp.delete_cookie("buyer_session")
    resp.delete_cookie("seller_session")
    return resp

# Buyer Admin Portal Dashboard
@app.get("/admin/dashboard", response_class=HTMLResponse)
def admin_dashboard(request: Request):
    user = get_current_user(request)
    if not user or user.get("role") != "admin":
        return RedirectResponse(url="/login", status_code=303)

    client = DatabaseService.get_supabase_client()
    try:
        buyers_res = client.table("profiles").select("*").execute()
        buyers = buyers_res.data if buyers_res.data else []
    except Exception:
        buyers = []

    history = DatabaseService.get_procurement_history()
    total_spending = sum(item.get("totalCost", 0) for item in history)

    return templates.TemplateResponse(request=request, name="admin_dashboard.html", context={
        "user": user,
        "buyers": buyers,
        "history": history,
        "total_spending": total_spending
    })

# ============================================================
# TECHNICAL SEO & CRAWLING ENDPOINTS
# ============================================================

@app.exception_handler(404)
def custom_404_handler(request: Request, __):
    meta_context = SEOService.generate_meta_context(
        path=request.url.path,
        title="404 Page Not Found | BharatLink Nexus AI",
        description="The requested page, craft category, or catalog product could not be found.",
        noindex=True
    )
    user = get_current_user(request)
    return templates.TemplateResponse(request=request, name="404.html", context={"user": user, "meta_context": meta_context}, status_code=404)

@app.get("/robots.txt", response_class=PlainTextResponse)
def robots_txt():
    domain = SEOService.get_domain()
    content = f"""User-agent: *
Allow: /
Allow: /procure
Allow: /how-it-works
Allow: /about
Allow: /contact
Allow: /privacy
Allow: /terms
Allow: /resources
Allow: /resources/*
Allow: /crafts
Allow: /crafts/*
Allow: /regions
Allow: /regions/*
Allow: /products/*
Allow: /seller-central
Allow: /seller-central/login
Allow: /seller-central/signup
Allow: /seller-central/tips

Disallow: /dashboard
Disallow: /profile
Disallow: /history
Disallow: /saved
Disallow: /admin/
Disallow: /api/
Disallow: /seller-central/dashboard
Disallow: /seller-central/inventory
Disallow: /seller-central/products
Disallow: /seller-central/reviews
Disallow: /seller-central/gallery
Disallow: /seller-central/analytics
Disallow: /seller-central/profile
Disallow: /seller-central/admin/

Sitemap: {domain}/sitemap.xml
"""
    return PlainTextResponse(content=content, media_type="text/plain")

@app.get("/sitemap.xml", response_class=Response)
def sitemap_xml():
    domain = SEOService.get_domain()
    
    routes = [
        {"path": "/", "priority": "1.0", "changefreq": "daily"},
        {"path": "/how-it-works", "priority": "0.9", "changefreq": "weekly"},
        {"path": "/crafts", "priority": "0.9", "changefreq": "daily"},
        {"path": "/regions", "priority": "0.8", "changefreq": "weekly"},
        {"path": "/resources", "priority": "0.8", "changefreq": "weekly"},
        {"path": "/seller-central", "priority": "0.9", "changefreq": "weekly"},
        {"path": "/about", "priority": "0.7", "changefreq": "monthly"},
        {"path": "/contact", "priority": "0.7", "changefreq": "monthly"},
        {"path": "/privacy", "priority": "0.3", "changefreq": "yearly"},
        {"path": "/terms", "priority": "0.3", "changefreq": "yearly"},
    ]

    for craft_slug in SEOService.get_craft_catalog().keys():
        routes.append({"path": f"/crafts/{craft_slug}", "priority": "0.85", "changefreq": "weekly"})

    for region_slug in SEOService.get_region_catalog().keys():
        routes.append({"path": f"/regions/{region_slug}", "priority": "0.80", "changefreq": "weekly"})

    for article_slug in ARTICLES_CATALOG.keys():
        routes.append({"path": f"/resources/{article_slug}", "priority": "0.75", "changefreq": "monthly"})

    try:
        db_products = DatabaseService.get_products()
        for p in db_products:
            if p.get("id"):
                routes.append({"path": f"/products/{p['id']}", "priority": "0.80", "changefreq": "daily"})
    except Exception:
        pass

    xml_entries = []
    for r in routes:
        loc = f"{domain}{r['path']}"
        xml_entries.append(f"  <url>\n    <loc>{loc}</loc>\n    <changefreq>{r['changefreq']}</changefreq>\n    <priority>{r['priority']}</priority>\n  </url>")

    xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(xml_entries)}
</urlset>"""

    return Response(content=xml_content, media_type="application/xml")

@app.get("/llms.txt", response_class=PlainTextResponse)
def llms_txt():
    domain = SEOService.get_domain()
    content = f"""# BharatLink Nexus AI — Platform Architecture & Entity Summary

> Primary Brand: BharatLink Nexus AI
> Website: {domain}
> Core Positioning: AI-Powered Artisan Procurement & Intelligent Multi-Modal Logistics Platform

## Platform Overview
BharatLink Nexus AI connects institutional B2B procurement buyers with verified Indian handicraft artisans, weavers, and MSMEs.
It features a 6-agent LangGraph workflow running Groq's `openai/gpt-oss-20b` LLM to evaluate 444+ GI-certified catalog products, verify active inventory, and map visual ASCII transit corridors.

## Key Public Sections
- AI Procurement Studio: {domain}/procure
- How It Works Architecture: {domain}/how-it-works
- Indian Craft Taxonomy: {domain}/crafts
- Regional Craft Clusters: {domain}/regions
- Knowledge Hub & Guides: {domain}/resources
- Seller Central Portal: {domain}/seller-central
"""
    return PlainTextResponse(content=content, media_type="text/plain")

# ============================================================
# BUYER PLATFORM PUBLIC & INDEXABLE CONTENT ROUTES
# ============================================================

@app.get("/", response_class=HTMLResponse)
def page_home(request: Request):
    user = get_current_user(request)
    meta_context = SEOService.generate_meta_context(
        path="/",
        title="BharatLink Nexus AI | AI-Powered Indian Artisan Procurement & Logistics",
        description="Discover authentic Indian artisan products with AI-powered supplier sourcing, inventory-aware procurement and intelligent logistics planning for domestic and international buyers."
    )
    return templates.TemplateResponse(request=request, name="index.html", context={"user": user, "active_page": "home", "meta_context": meta_context})

@app.get("/how-it-works", response_class=HTMLResponse)
def page_how_it_works(request: Request):
    user = get_current_user(request)
    meta_context = SEOService.generate_meta_context(
        path="/how-it-works",
        title="How AI Procurement Works | BharatLink Nexus AI",
        description="Learn how our 6-agent LangGraph workflow evaluates Indian artisan products, verifies stock inventory, maps transit corridors, and assesses weather risks.",
        breadcrumbs=[{"name": "Home", "url": "/"}, {"name": "How It Works", "url": "/how-it-works"}]
    )
    return templates.TemplateResponse(request=request, name="how_it_works.html", context={"user": user, "active_page": "how_it_works", "meta_context": meta_context})

@app.get("/about", response_class=HTMLResponse)
def page_about(request: Request):
    user = get_current_user(request)
    meta_context = SEOService.generate_meta_context(
        path="/about",
        title="About BharatLink Nexus AI | Indian Artisan Procurement Platform",
        description="Connecting global B2B procurement buyers directly with verified Indian artisan collectives, GI tag authentication, and intelligent freight logistics.",
        breadcrumbs=[{"name": "Home", "url": "/"}, {"name": "About", "url": "/about"}]
    )
    return templates.TemplateResponse(request=request, name="about.html", context={"user": user, "active_page": "about", "meta_context": meta_context})

@app.get("/contact", response_class=HTMLResponse)
def page_contact(request: Request):
    user = get_current_user(request)
    meta_context = SEOService.generate_meta_context(
        path="/contact",
        title="Contact BharatLink Nexus AI | Buyer & Seller Inquiries",
        description="Contact our team for B2B artisan procurement assistance, bulk export orders, or Seller Central artisan onboarding.",
        breadcrumbs=[{"name": "Home", "url": "/"}, {"name": "Contact", "url": "/contact"}]
    )
    return templates.TemplateResponse(request=request, name="contact.html", context={"user": user, "active_page": "contact", "meta_context": meta_context})

@app.post("/contact", response_class=HTMLResponse)
def submit_contact_query(request: Request, full_name: str = Form(...), email: str = Form(...), query: str = Form(...)):
    user = get_current_user(request)
    meta_context = SEOService.generate_meta_context(
        path="/contact",
        title="Contact BharatLink Nexus AI | Buyer & Seller Inquiries",
        description="Contact our team for B2B artisan procurement assistance.",
        breadcrumbs=[{"name": "Home", "url": "/"}, {"name": "Contact", "url": "/contact"}]
    )
    
    EmailService.send_contact_inquiry(full_name=full_name, sender_email=email, query_text=query)
    
    success_msg = f"Thank you, {full_name}! Your inquiry has been sent directly to Shravan Shidruk (shravanshidruk1605@gmail.com). We will contact you at {email} within 24 hours."
    
    return templates.TemplateResponse(request=request, name="contact.html", context={
        "user": user,
        "active_page": "contact",
        "meta_context": meta_context,
        "success_msg": success_msg
    })

@app.post("/api/contact")
def api_contact_submit(req: ContactInquiryRequest):
    EmailService.send_contact_inquiry(full_name=req.fullName, sender_email=req.email, query_text=req.query)
    return {
        "success": True,
        "message": f"Inquiry submitted successfully to Shravan Shidruk (shravanshidruk1605@gmail.com).",
        "recipient": "shravanshidruk1605@gmail.com"
    }

@app.get("/privacy", response_class=HTMLResponse)
def page_privacy(request: Request):
    user = get_current_user(request)
    meta_context = SEOService.generate_meta_context(
        path="/privacy",
        title="Privacy Policy | BharatLink Nexus AI",
        description="Read the privacy policy and data protection guidelines for BharatLink Nexus AI buyers and sellers.",
        breadcrumbs=[{"name": "Home", "url": "/"}, {"name": "Privacy Policy", "url": "/privacy"}]
    )
    return templates.TemplateResponse(request=request, name="privacy.html", context={"user": user, "active_page": "privacy", "meta_context": meta_context})

@app.get("/terms", response_class=HTMLResponse)
def page_terms(request: Request):
    user = get_current_user(request)
    meta_context = SEOService.generate_meta_context(
        path="/terms",
        title="Terms of Service | BharatLink Nexus AI",
        description="Terms of service and B2B procurement disclaimers for BharatLink Nexus AI platform.",
        breadcrumbs=[{"name": "Home", "url": "/"}, {"name": "Terms of Service", "url": "/terms"}]
    )
    return templates.TemplateResponse(request=request, name="terms.html", context={"user": user, "active_page": "terms", "meta_context": meta_context})

@app.get("/resources", response_class=HTMLResponse)
def page_resources(request: Request):
    user = get_current_user(request)
    meta_context = SEOService.generate_meta_context(
        path="/resources",
        title="Procurement & Artisan Knowledge Hub | BharatLink Nexus AI",
        description="In-depth educational guides on AI procurement, GI tag handlooms, regional craft traditions, and international logistics.",
        breadcrumbs=[{"name": "Home", "url": "/"}, {"name": "Resources", "url": "/resources"}]
    )
    return templates.TemplateResponse(request=request, name="resources.html", context={"user": user, "active_page": "resources", "articles": ARTICLES_CATALOG, "meta_context": meta_context})

@app.get("/resources/{article_slug}", response_class=HTMLResponse)
def page_resource_article(request: Request, article_slug: str):
    user = get_current_user(request)
    article = ARTICLES_CATALOG.get(article_slug)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    meta_context = SEOService.generate_meta_context(
        path=f"/resources/{article_slug}",
        title=f"{article['title']} | BharatLink Nexus AI",
        description=article['summary'],
        breadcrumbs=[
            {"name": "Home", "url": "/"},
            {"name": "Resources", "url": "/resources"},
            {"name": article['title'], "url": f"/resources/{article_slug}"}
        ]
    )
    return templates.TemplateResponse(request=request, name="resource_article.html", context={"user": user, "article": article, "meta_context": meta_context})

@app.get("/crafts", response_class=HTMLResponse)
def page_crafts(request: Request):
    user = get_current_user(request)
    crafts = SEOService.get_craft_catalog()
    meta_context = SEOService.generate_meta_context(
        path="/crafts",
        title="Indian Handicrafts & Artisan Products | BharatLink Nexus AI",
        description="Discover authentic GI-certified Indian handloom textiles, pottery, metalwork, leather crafts, and folk art.",
        breadcrumbs=[{"name": "Home", "url": "/"}, {"name": "Crafts", "url": "/crafts"}]
    )
    return templates.TemplateResponse(request=request, name="craft_detail.html", context={"user": user, "active_page": "crafts", "is_index": True, "crafts": crafts, "meta_context": meta_context})

@app.get("/crafts/{craft_slug}", response_class=HTMLResponse)
def page_craft_detail(request: Request, craft_slug: str):
    user = get_current_user(request)
    crafts = SEOService.get_craft_catalog()
    craft = crafts.get(craft_slug)
    if not craft:
        raise HTTPException(status_code=404, detail="Craft category not found")

    all_products = DatabaseService.get_products()
    matching = [p for p in all_products if (craft_slug.replace('-', ' ') in p.get('category', '').lower() or craft_slug.replace('-', ' ') in p.get('name', '').lower() or craft['name'].lower() in p.get('name', '').lower())]

    meta_context = SEOService.generate_meta_context(
        path=f"/crafts/{craft_slug}",
        title=f"{craft['name']} | BharatLink Nexus AI",
        description=craft['description'],
        breadcrumbs=[
            {"name": "Home", "url": "/"},
            {"name": "Crafts", "url": "/crafts"},
            {"name": craft['name'], "url": f"/crafts/{craft_slug}"}
        ]
    )
    return templates.TemplateResponse(request=request, name="craft_detail.html", context={"user": user, "active_page": "crafts", "is_index": False, "craft": craft, "products": matching, "meta_context": meta_context})

@app.get("/regions", response_class=HTMLResponse)
def page_regions(request: Request):
    user = get_current_user(request)
    regions = SEOService.get_region_catalog()
    meta_context = SEOService.generate_meta_context(
        path="/regions",
        title="Indian Artisan Regions & Craft Clusters | BharatLink Nexus AI",
        description="Explore verified artisan hubs across Maharashtra, Rajasthan, Gujarat, and Kashmir.",
        breadcrumbs=[{"name": "Home", "url": "/"}, {"name": "Regions", "url": "/regions"}]
    )
    return templates.TemplateResponse(request=request, name="region_detail.html", context={"user": user, "active_page": "regions", "is_index": True, "regions": regions, "meta_context": meta_context})

@app.get("/regions/{region_slug}", response_class=HTMLResponse)
def page_region_detail(request: Request, region_slug: str):
    user = get_current_user(request)
    regions = SEOService.get_region_catalog()
    region = regions.get(region_slug)
    if not region:
        raise HTTPException(status_code=404, detail="Regional cluster not found")

    meta_context = SEOService.generate_meta_context(
        path=f"/regions/{region_slug}",
        title=f"{region['name']} | BharatLink Nexus AI",
        description=region['description'],
        breadcrumbs=[
            {"name": "Home", "url": "/"},
            {"name": "Regions", "url": "/regions"},
            {"name": region['name'], "url": f"/regions/{region_slug}"}
        ]
    )
    return templates.TemplateResponse(request=request, name="region_detail.html", context={"user": user, "active_page": "regions", "is_index": False, "region": region, "meta_context": meta_context})

@app.get("/products/{product_id}", response_class=HTMLResponse)
def page_product_detail(request: Request, product_id: str):
    user = get_current_user(request)
    all_products = DatabaseService.get_products()
    product = next((p for p in all_products if str(p.get("id")) == str(product_id)), None)

    if not product or not product.get("active", True):
        raise HTTPException(status_code=404, detail="Product not found or unpublished")

    domain = SEOService.get_domain()
    raw_img = product.get("image_url") or ""
    img_url = raw_img if (raw_img.startswith("http") or raw_img.startswith("/static")) else f"{domain}/static/images/logo.png"

    product_schema = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": product.get("name"),
        "description": product.get("description") or f"Authentic {product.get('category')} crafted by {product.get('seller_name')} in {product.get('region')}.",
        "image": img_url,
        "category": product.get("category"),
        "brand": {
            "@type": "Brand",
            "name": product.get("seller_name", "Artisan Guild")
        },
        "offers": {
            "@type": "Offer",
            "price": float(product.get("price", 0)),
            "priceCurrency": "INR",
            "availability": "https://schema.org/InStock" if int(product.get("available_stock", 0)) > 0 else "https://schema.org/OutOfStock",
            "seller": {
                "@type": "Organization",
                "name": product.get("seller_name", "Artisan Guild")
            }
        }
    }

    meta_context = SEOService.generate_meta_context(
        path=f"/products/{product_id}",
        title=f"{product.get('name')} | BharatLink Nexus AI",
        description=f"Source authentic {product.get('name')} by {product.get('seller_name')} ({product.get('region')}). Unit price: ₹{float(product.get('price', 0)):,.2f}.",
        og_image=img_url,
        og_type="product",
        breadcrumbs=[
            {"name": "Home", "url": "/"},
            {"name": "Crafts", "url": "/crafts"},
            {"name": product.get("name"), "url": f"/products/{product_id}"}
        ],
        schema_data=[product_schema]
    )

    return templates.TemplateResponse(request=request, name="product_detail.html", context={"user": user, "product": product, "meta_context": meta_context})

# ============================================================
# PRIVATE BUYER USER ROUTES (WITH NOINDEX CONTROL)
# ============================================================

@app.get("/procure", response_class=HTMLResponse)
def page_procure(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    meta_context = SEOService.generate_meta_context(
        path="/procure",
        title="AI Procurement Studio | BharatLink Nexus AI",
        description="Autonomous AI procurement studio for institutional buyers.",
        noindex=True
    )
    return templates.TemplateResponse(request=request, name="procure.html", context={"user": user, "active_page": "procure", "meta_context": meta_context})

@app.get("/dashboard", response_class=HTMLResponse)
def page_dashboard(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    history = DatabaseService.get_procurement_history(user_id=user["id"])
    products = DatabaseService.get_products()
    sellers = DatabaseService.get_sellers()

    meta_context = SEOService.generate_meta_context(
        path="/dashboard",
        title="Buyer Dashboard | BharatLink Nexus AI",
        description="Private procurement management dashboard.",
        noindex=True
    )

    return templates.TemplateResponse(request=request, name="dashboard.html", context={
        "user": user,
        "active_page": "dashboard",
        "history": history,
        "products": products,
        "sellers": sellers,
        "meta_context": meta_context
    })

@app.get("/history", response_class=HTMLResponse)
def page_history(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    history = DatabaseService.get_procurement_history(user_id=user["id"])
    meta_context = SEOService.generate_meta_context(
        path="/history",
        title="Procurement History | BharatLink Nexus AI",
        description="Private procurement audit logs.",
        noindex=True
    )
    return templates.TemplateResponse(request=request, name="history.html", context={
        "user": user,
        "active_page": "history",
        "history": history,
        "meta_context": meta_context
    })

@app.get("/saved", response_class=HTMLResponse)
def page_saved(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    history = DatabaseService.get_procurement_history(user_id=user["id"])
    meta_context = SEOService.generate_meta_context(
        path="/saved",
        title="Saved Procurement Plans | BharatLink Nexus AI",
        description="Private saved sourcing plans.",
        noindex=True
    )
    return templates.TemplateResponse(request=request, name="saved.html", context={
        "user": user,
        "active_page": "saved",
        "history": history[:2],
        "meta_context": meta_context
    })

@app.get("/profile", response_class=HTMLResponse)
def page_profile(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    meta_context = SEOService.generate_meta_context(
        path="/profile",
        title="Buyer Profile | BharatLink Nexus AI",
        description="Private account preferences.",
        noindex=True
    )
    return templates.TemplateResponse(request=request, name="profile.html", context={"user": user, "active_page": "profile", "meta_context": meta_context})

# ============================================================
# SELLER CENTRAL PLATFORM ROUTES
# ============================================================

@app.get("/seller-central", response_class=HTMLResponse)
def seller_portal(request: Request):
    seller_user = get_current_seller(request)
    meta_context = SEOService.generate_meta_context(
        path="/seller-central",
        title="BharatLink Seller Central | Sell Indian Handicrafts Internationally",
        description="Manage Indian artisan products, inventory and seller information with BharatLink Nexus AI Seller Central and connect your products with global procurement opportunities.",
        breadcrumbs=[{"name": "Home", "url": "/"}, {"name": "Seller Central", "url": "/seller-central"}]
    )
    return templates.TemplateResponse(request=request, name="seller/portal.html", context={"seller_user": seller_user, "active_page": "portal", "meta_context": meta_context})

@app.get("/seller-central/login", response_class=HTMLResponse)
def seller_login_page(request: Request):
    return templates.TemplateResponse(request=request, name="seller/login.html", context={})

@app.post("/seller-central/login", response_class=HTMLResponse)
def seller_login_submit(request: Request, email: str = Form(...), password: str = Form(...)):
    res = AuthService.login_user(email, password)
    if res["success"]:
        user = res["user"]
        if user.get("role") == "admin":
            resp = RedirectResponse(url="/seller-central/admin/dashboard", status_code=303)
            resp.set_cookie(key="seller_session", value=json.dumps({"user": user, "role": "admin", "email": email}), max_age=86400)
            return resp

        seller = AuthService.get_seller_by_user_id(user["id"])
        resp = RedirectResponse(url="/seller-central/dashboard", status_code=303)
        resp.set_cookie(key="seller_session", value=json.dumps({"user": user, "seller": seller, "email": email}), max_age=86400)
        return resp

    return templates.TemplateResponse(request=request, name="seller/login.html", context={"error": res.get("error", "Seller login failed")})

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

    return templates.TemplateResponse(request=request, name="seller/signup.html", context={"error": res.get("error", "Registration failed")})

@app.get("/seller-central/dashboard", response_class=HTMLResponse)
def seller_dashboard(request: Request):
    seller_user = get_current_seller(request)
    if not seller_user:
        return RedirectResponse(url="/seller-central/login", status_code=303)

    user = seller_user.get("user") or {}
    is_admin = (user.get("role") == "admin" or user.get("email") == "admin@bharatlink.com")

    seller_info = seller_user.get("seller") if seller_user else None
    seller_id = seller_info.get("id") if seller_info else None
    seller_business_name = seller_info.get("business_name") if seller_info else None

    if is_admin:
        products = DatabaseService.get_products()
        sellers = DatabaseService.get_sellers(active_only=False)
        analytics = DatabaseService.get_admin_analytics()
    else:
        products = DatabaseService.get_products(seller_id=seller_id) if seller_id else []
        sellers = DatabaseService.get_sellers()
        analytics = DatabaseService.get_seller_analytics(seller_business_name=seller_business_name, seller_id=seller_id)

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
    is_admin = (user.get("role") == "admin" or user.get("email") == "admin@bharatlink.com")

    seller_info = seller_user.get("seller") if seller_user else None
    seller_id = seller_info.get("id") if seller_info else None

    if is_admin:
        products = DatabaseService.get_products()
    else:
        products = DatabaseService.get_products(seller_id=seller_id) if seller_id else []

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
    seller_info = seller_user.get("seller") if seller_user else None
    seller_id = seller_info.get("id") if seller_info else None
    seller_name = seller_info.get("business_name") if seller_info else "Artisan Guild"

    DatabaseService.add_product({
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
    })

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
    update_data = {
        "name": name,
        "description": description,
        "category": category,
        "region": region,
        "price": price,
        "available_stock": availableStock,
        "image_url": imageUrl
    }
    DatabaseService.update_product_full(productId, update_data)
    return RedirectResponse(url="/seller-central/products", status_code=303)

@app.post("/seller-central/products/delete")
def seller_product_delete_submit(req: ProductDeleteRequest):
    return DatabaseService.delete_product(req.productId)

@app.get("/seller-central/inventory", response_class=HTMLResponse)
def seller_inventory(request: Request):
    seller_user = get_current_seller(request)
    if not seller_user:
        return RedirectResponse(url="/seller-central/login", status_code=303)

    user = seller_user.get("user") or {}
    is_admin = (user.get("role") == "admin" or user.get("email") == "admin@bharatlink.com")

    seller_info = seller_user.get("seller") if seller_user else None
    seller_business_name = seller_info.get("business_name") if seller_info else None
    seller_id = seller_info.get("id") if seller_info else None

    if is_admin:
        products = DatabaseService.get_products()
        analytics = DatabaseService.get_admin_analytics()
    else:
        products = DatabaseService.get_products(seller_id=seller_id) if seller_id else []
        analytics = DatabaseService.get_seller_analytics(seller_business_name=seller_business_name, seller_id=seller_id)

    return templates.TemplateResponse(request=request, name="seller/inventory.html", context={
        "seller_user": seller_user,
        "active_page": "inventory",
        "products": products,
        "analytics": analytics,
        "is_admin": is_admin
    })

@app.post("/seller-central/inventory/update")
def seller_inventory_update(req: StockUpdateRequest):
    return DatabaseService.update_stock(req.productId, req.availableStock)

@app.post("/seller-central/inventory/update-order-status")
def seller_order_status_update(req: OrderStatusUpdateRequest):
    return DatabaseService.update_order_status(req.orderId, req.status)

# 100% REAL DATABASE ANALYTICS FOR SELLERS
@app.get("/seller-central/reviews", response_class=HTMLResponse)
def seller_reviews(request: Request):
    seller_user = get_current_seller(request)
    user = seller_user.get("user") or {}
    is_admin = (user.get("role") == "admin" or user.get("email") == "admin@bharatlink.com")

    seller_info = seller_user.get("seller") if seller_user else None
    seller_business_name = seller_info.get("business_name") if seller_info else None
    seller_id = seller_info.get("id") if seller_info else None

    if is_admin:
        analytics = DatabaseService.get_admin_analytics()
    else:
        analytics = DatabaseService.get_seller_analytics(seller_business_name=seller_business_name, seller_id=seller_id)

    return templates.TemplateResponse(request=request, name="seller/reviews.html", context={
        "seller_user": seller_user,
        "active_page": "reviews",
        "analytics": analytics,
        "is_admin": is_admin
    })

@app.get("/seller-central/gallery", response_class=HTMLResponse)
def seller_gallery(request: Request):
    seller_user = get_current_seller(request)
    user = seller_user.get("user") or {}
    is_admin = (user.get("role") == "admin" or user.get("email") == "admin@bharatlink.com")

    seller_info = seller_user.get("seller") if seller_user else None
    seller_id = seller_info.get("id") if seller_info else None

    if is_admin:
        products = DatabaseService.get_products()
    else:
        products = DatabaseService.get_products(seller_id=seller_id) if seller_id else []

    return templates.TemplateResponse(request=request, name="seller/gallery.html", context={"seller_user": seller_user, "active_page": "gallery", "products": products, "is_admin": is_admin})

@app.get("/seller-central/analytics", response_class=HTMLResponse)
def seller_analytics(request: Request):
    seller_user = get_current_seller(request)
    user = seller_user.get("user") or {}
    is_admin = (user.get("role") == "admin" or user.get("email") == "admin@bharatlink.com")

    seller_info = seller_user.get("seller") if seller_user else None
    seller_business_name = seller_info.get("business_name") if seller_info else None
    seller_id = seller_info.get("id") if seller_info else None

    if is_admin:
        analytics = DatabaseService.get_admin_analytics()
    else:
        analytics = DatabaseService.get_seller_analytics(seller_business_name=seller_business_name, seller_id=seller_id)

    return templates.TemplateResponse(request=request, name="seller/analytics.html", context={
        "seller_user": seller_user,
        "active_page": "analytics",
        "analytics": analytics,
        "is_admin": is_admin
    })

@app.get("/seller-central/analytics", response_class=HTMLResponse)
def seller_analytics(request: Request):
    seller_user = get_current_seller(request)
    seller_info = seller_user.get("seller") if seller_user else None
    seller_business_name = seller_info.get("business_name") if seller_info else None
    seller_id = seller_info.get("id") if seller_info else None

    analytics = DatabaseService.get_seller_analytics(seller_business_name=seller_business_name, seller_id=seller_id)

    return templates.TemplateResponse(request=request, name="seller/analytics.html", context={
        "seller_user": seller_user,
        "active_page": "analytics",
        "analytics": analytics
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

# Seller Admin Moderation Dashboard
@app.get("/seller-central/admin/dashboard", response_class=HTMLResponse)
def seller_admin_dashboard(request: Request):
    seller_user = get_current_seller(request)
    user = seller_user.get("user") if seller_user else None
    if not user or user.get("role") != "admin":
        return RedirectResponse(url="/seller-central/login", status_code=303)

    sellers = DatabaseService.get_sellers(active_only=False)
    products = DatabaseService.get_products()

    return templates.TemplateResponse(request=request, name="seller/admin_dashboard.html", context={
        "seller_user": seller_user,
        "sellers": sellers,
        "products": products
    })

@app.post("/seller-central/admin/approve")
def seller_admin_approve(request: Request, seller_id: str = Form(...)):
    AuthService.approve_seller(seller_id)
    return RedirectResponse(url="/seller-central/admin/dashboard", status_code=303)

@app.post("/seller-central/admin/deactivate")
def seller_admin_deactivate(request: Request, seller_id: str = Form(...)):
    AuthService.deactivate_seller(seller_id)
    return RedirectResponse(url="/seller-central/admin/dashboard", status_code=303)

# ============================================================
# API ENDPOINTS
# ============================================================

@app.post("/api/procurement")
def run_procurement(request: Request, req: ProcurementRequest):
    if not req.prompt or not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt parameter is required.")

    user = get_current_user(request)
    user_id = user["id"] if user else None

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

        # Clear large state objects and trigger RAM memory trim
        del final_state
        del initial_input
        gc.collect()

        return response_data
    except Exception as e:
        print("Error executing Python LangGraph workflow:", e)
        gc.collect()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/history")
def get_history(request: Request):
    user = get_current_user(request)
    user_id = user["id"] if user else None
    return {"history": DatabaseService.get_procurement_history(user_id=user_id)}

@app.post("/api/procurement/whatsapp")
def track_whatsapp_contact(req: WhatsAppStatusRequest):
    return {"success": True, "status": req.status, "message": "Procurement status updated: Seller Contacted via WhatsApp"}

import socket

def is_port_free(port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            return s.connect_ex(('127.0.0.1', port)) != 0
    except Exception:
        return False

if __name__ == "__main__":
    target_port = 8000
    for p in [8000, 8001, 8080, 5000, 5001]:
        if is_port_free(p):
            target_port = p
            break

    print(f"Starting BharatLink Nexus AI on http://localhost:{target_port}")
    uvicorn.run("main:app", host="127.0.0.1", port=target_port, reload=False)
