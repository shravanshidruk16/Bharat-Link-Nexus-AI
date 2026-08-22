# BharatLink Nexus AI — Seller Central

**Tagline**: Artisan Inventory, Product Catalog, & Weather-Aware Logistics Gateway

BharatLink Nexus AI Seller Central is the seller-facing inventory and logistics management platform powering the **BharatLink Nexus AI** buyer-facing procurement platform.

---

## 🌟 Key Capabilities

1. **Artisan Guild & Seller Onboarding**
   - Business profile registration, craft category, artisan count, and GI Tag certification verification (`Verified`, `Demo Verified`, `Pending`).
2. **Product Catalog & Dimensions Management**
   - Full CRUD for products including unit price, available stock, MOQ, weight (kg), dimensions (L × W × H cm), craft tags, and authenticity status.
3. **Real-Time Inventory Control**
   - Stock level adjustments (e.g. 75 → 45 units) immediately synchronize with AI Buyer eligibility calculations.
4. **Logistics & Weather Gateway**
   - Integrations & Abstractions: **Aviationstack** (Flight operational route schedules), **Indian Rail API** (Rail freight corridors), **SeaRates / Freightos** (Ocean freight rate quotes), and **WeatherAPI** (Transit hub weather alerts).
   - **Resilient Fallback Mode**: Prototype fallback data tagged `LIVE`, `ESTIMATE`, `CACHED`, `SIMULATED`.
   - **Weather-Aware Route Engine**: Evaluates Air, Sea, Rail, Road, and Multimodal corridors based on priority (`FASTEST`, `CHEAPEST`, `BALANCED`, `LOWEST RISK`, `LOWEST CARBON`).
5. **Public REST API Layer for AI Agents**
   - Exposes `/api/public/*` endpoints consumed directly by the 6 AI Agents in the main buyer platform.

---

## 🚀 Quick Navigation

- **Seller Dashboard**: `/seller-central/dashboard`
- **Product Management**: `/seller-central/products`
- **Add Product**: `/seller-central/products/new`
- **Inventory Control**: `/seller-central/inventory`
- **Logistics Calculator**: `/seller-central/logistics`
- **API Tracker**: `/seller-central/transportation`
- **Profile & Verification**: `/seller-central/profile`
