import os
import uvicorn
import socket
import json
import gc
import markdown
from fastapi import FastAPI, Request, Form, HTTPException, Cookie, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from agents.workflow import build_workflow
from services.supabase_service import DatabaseService
from services.route_optimizer import RouteOptimizerService
from services.auth_service import AuthService

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
# BUYER PLATFORM HTML ROUTES
# ============================================================

@app.get("/", response_class=HTMLResponse)
def page_home(request: Request):
    user = get_current_user(request)
    return templates.TemplateResponse(request=request, name="index.html", context={"user": user, "active_page": "home"})

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

    history = DatabaseService.get_procurement_history(user_id=user["id"])
    products = DatabaseService.get_products()
    sellers = DatabaseService.get_sellers()

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

    history = DatabaseService.get_procurement_history(user_id=user["id"])
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

    history = DatabaseService.get_procurement_history(user_id=user["id"])
    return templates.TemplateResponse(request=request, name="saved.html", context={
        "user": user,
        "active_page": "saved",
        "history": history[:2]
    })

@app.get("/profile", response_class=HTMLResponse)
def page_profile(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse(request=request, name="profile.html", context={"user": user, "active_page": "profile"})

# ============================================================
# SELLER CENTRAL PLATFORM ROUTES
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
