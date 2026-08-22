# Seller Central Public REST API Specification

This document details the public API endpoints exposed by **BharatLink Nexus AI Seller Central** for consumption by the 6 AI Agents in the main BharatLink buyer procurement platform.

---

## Endpoints Summary

### 1. Search Products
- **Endpoint**: `GET /api/public/products/search`
- **Query Parameters**:
  - `query` (optional): Free-text query matching product name, description, tags, region, category
  - `category` (optional): Filter by category (e.g. `Apparel & Textiles`, `Handicrafts & Decor`)
  - `region` (optional): Filter by artisan region (e.g. `Maharashtra`, `Jammu & Kashmir`)
  - `sellerId` (optional): Filter by seller ID
  - `maxPrice` (optional): Maximum price in INR
  - `minQuantity` (optional): Minimum available stock requirement
- **Response**: JSON array of matching `SellerProduct` records.

### 2. Product Details
- **Endpoint**: `GET /api/public/products/:id`
- **Response**: Detailed specifications (price, availableStock, weightKg, lengthCm, widthCm, heightCm, GI certification tag).

### 3. Check Inventory
- **Endpoint**: `GET /api/public/inventory/:productId?requiredQuantity=50`
- **Response**: `{ available: boolean, stock: number, minimumOrderQuantity: number }`.

### 4. Search Sellers
- **Endpoint**: `GET /api/public/sellers/search`
- **Response**: Array of registered sellers, GI craft certifications, and verification statuses (`Verified`, `Demo Verified`, `Pending`).

### 5. Calculate Logistics Shipping Quote
- **Endpoint**: `POST /api/public/logistics/quote`
- **Request Body**:
  ```json
  {
    "originCity": "Yeola, Maharashtra",
    "destinationCity": "London, UK",
    "weightKg": 20,
    "quantity": 50,
    "requiredDeliveryDays": 10,
    "priorityPreference": "BALANCED"
  }
  ```
- **Response**: Normalized transport options across Air Express, Air Freight, Rail, Ocean, and Multimodal corridors, with CO₂ calculations, ETA, freight charges, data freshness tags (`LIVE`, `ESTIMATE`, `CACHED`), and transit hub weather alert warnings.
