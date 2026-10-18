# BharatLink Nexus AI — Google AI Builder Cup Demonstration Walkthrough

## 1. Challenge Demonstration Overview

**Challenge Theme**: Retail & Commerce: Intelligent Customer and Business Experiences  
**Platform**: BharatLink Nexus AI — Agentic Retail & Commerce Intelligence Platform  
**Target Solution**: Connecting institutional buyers with authentic Indian artisan collectives using Google Gemini, Firebase, and Cloud Run, while empowering sellers and retailers with predictive demand intelligence, real-time inventory management, and grounded conversational discovery.

---

## 2. End-to-End Demonstration Workflow

### Scene 1: Buyer Conversational Procurement & Grounded Discovery
1. **User Persona**: Institutional buyer seeking authentic handloom textiles for retail export.
2. **Action**:
   - Navigate to `/procure`.
   - Enter natural language prompt: *"Source 50 units of authentic Nauvari Paithani Sarees with GI tag certification for export to London within 10 days. Target budget INR 500,000."*
   - Click **Run 6-Agent Sourcing Workflow**.
3. **What Happens Behind the Scenes**:
   - **Buyer Intent Agent** invokes Google Gemini (`gemini-2.5-flash`) to extract: product type ("Paithani Saree"), category ("Textiles & Apparel"), quantity (50), destination ("London"), deadline (10 days).
   - **Product & Supplier Discovery Agent** queries Cloud Firestore for verified GI-certified artisan sellers matching Paithani Sarees.
   - **Procurement Evaluation Agent** checks stock availability, computes deterministic product costs (`₹10,500 * 50 = ₹525,000`), and ranks candidate sellers.
   - **Logistics Corridor Agent** maps the visual ASCII transit route (`[ Origin: Yeola/Nashik ] ──► [ Air Cargo Hub: Mumbai BOM ] ──► [ Heathrow LHR: London ]`).
   - **Risk Assessment Agent** calls real-time weather API to assess meteorological corridor safety.
   - **Decision & Explanation Agent** synthesizes an executive sourcing recommendation with verified artisan contacts.
4. **Key Takeaway**: Zero LLM hallucination of prices or inventory. Grounded in actual Firestore catalog data.

---

### Scene 2: Interactive Shopping Assistant & Personalization
1. **Action**:
   - Open the **Conversational Shopping Assistant** widget on the buyer dashboard.
   - Set buyer preferences in `/profile`: Select preferred categories (e.g. *Handicrafts & Handloom*, *Organic Produce*).
   - Ask the assistant: *"Which wooden toys or decor items do you recommend for an eco-friendly boutique?"*
2. **What Happens**:
   - Assistant retrieves grounded in-stock items from Firestore, highlights GI certifications, and personalizes recommendations according to the buyer's saved preferences.

---

### Scene 3: Seller Central — Inventory Intelligence & Oversell Protection
1. **User Persona**: Artisan collective administrator.
2. **Action**:
   - Navigate to `/seller-central/inventory`.
   - View real-time inventory dashboard with **Low Stock Indicators** (`< 15 units`).
   - Attempt an inventory update for an artisan product.
3. **What Happens**:
   - Backend enforces seller ownership (a seller cannot edit another collective's stock).
   - Updates are executed via **ACID transactions** to prevent concurrent overselling.
   - An immutable movement entry is written to `inventory_movements` for auditing.

---

### Scene 4: Retail & Commerce Intelligence — Demand Forecasting & Basket Analysis
1. **Action**:
   - Navigate to `/seller-central/analytics`.
   - Review **Demand Forecast Engine**:
     - View 30-day and 60-day projected demand trends based on actual historical transactions.
     - View statistical confidence intervals and honest data availability labels.
   - Review **Market Basket Analysis**:
     - View frequently co-purchased artisan pairings (e.g., *Brass Diya + Paithani Saree*, *Ceramic Vase + Coasters*).
   - Query the **Business Decision Assistant**:
     - Ask: *"Which products are at risk of going out of stock this month?"*
     - Assistant executes deterministic database queries and provides grounded business advice.

---

### Scene 5: Administrator Security & Governance
1. **Action**:
   - Navigate to `/seller-central/admin/dashboard`.
   - Review seller verification requests and platform audit logs.
   - Confirm unauthenticated users and standard sellers cannot access administrative functions.
