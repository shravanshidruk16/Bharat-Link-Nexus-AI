# 🛍️ BharatLink Nexus AI — Autonomous B2B Artisan Sourcing & Intelligent Craft Logistics Platform

[![Deploy to Render](https://render.com/images/deploy-to-render.svg)](https://render.com)

**BharatLink Nexus AI** is an AI-powered B2B e-commerce procurement and multi-modal logistics platform connecting Indian GI-certified artisan weavers, craftsmen, and seller collectives with global buyers, institutional purchasers, and retail brands.

---

## 🌟 Key Features

1. **🤖 6-Agent LangGraph Procurement Engine**:
   - **Buyer Intent Agent**: Parses natural language requests into structured procurement parameters.
   - **Discovery Agent**: Searches verified Supabase artisan catalog database.
   - **Procurement Evaluation Agent**: Compares candidate artisan sellers, ratings, unit prices, and stock availability.
   - **Logistics Optimization Agent**: Calculates transit distance (km), fuel expenses (Diesel @ ₹100/L + tolls), and container vehicle mode.
   - **Risk & Disruption Agent**: Fetches real-time weather at origin and destination cities using Open-Meteo API.
   - **Decision & Explanation Agent**: Synthesizes structured executive procurement reports.

2. **🏬 Multi-Tenant Seller Central Portal**:
   - Multi-tenant seller isolation — each artisan seller manages their own products, stock levels, and order fulfillment.
   - Admin moderation approval workflow (`admin@bharatlink.com`) to approve/verify new seller registrations before catalog publishing.

3. **📱 Progressive Web App (PWA) & Mobile UI**:
   - Standalone PWA app manifest, service worker offline caching, and floating install prompt banner.
   - Fixed mobile bottom navigation bar (`🏠 Home`, `🤖 AI Procure`, `📊 Dashboard`, `📜 History`, `👤 Profile`).

4. **📄 PDF Sourcing Reports & Direct WhatsApp Inquiry**:
   - Download executive recommendation summaries as styled PDF reports.
   - Direct purchase inquiry connection to verified seller WhatsApp numbers.

---

## 🚀 Quick Start (Local Setup)

```bash
# 1. Clone repository
git clone https://github.com/shravanshidruk16/Bharat-Link-Nexus-AI.git
cd Bharat-Link-Nexus-AI

# 2. Set up virtual environment
python -m venv venv
venv\Scripts\activate  # On Windows
# source venv/bin/activate  # On Linux/macOS

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set Environment Variables
# Create .env file with:
# SUPABASE_URL=your_supabase_url
# SUPABASE_SERVICE_KEY=your_supabase_service_key
# GROQ_API_KEY=your_groq_api_key

# 5. Run application server
python main.py
```

Application will run at `http://localhost:8000`.

---

## ☁️ Deployment on Render

1. Create a new **Web Service** on [Render](https://render.com).
2. Connect your GitHub repository: `https://github.com/shravanshidruk16/Bharat-Link-Nexus-AI.git`.
3. Set **Build Command**: `pip install -r requirements.txt`.
4. Set **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`.
5. Add Environment Variables on Render dashboard:
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_KEY`
   - `GROQ_API_KEY`

---

## 📜 License

© 2026 BharatLink Nexus AI. All Rights Reserved.
