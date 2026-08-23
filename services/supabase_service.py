import re
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_SERVICE_KEY

def get_supabase_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def stem_word(w: str) -> str:
    """Normalize plurals and suffixes (e.g. mangoes -> mango, hoodies -> hoodie, sarees -> saree, rings -> ring)."""
    w = w.lower().strip()
    if w.endswith('ies') and len(w) > 4:
        return w[:-3] + 'y' if not w.endswith('hoodies') else 'hoodie'
    if w.endswith('es') and len(w) > 4:
        if w.endswith('mangoes'): return 'mango'
        if w.endswith('sarees'): return 'saree'
        return w[:-2]
    if w.endswith('s') and not w.endswith('ss') and len(w) > 3:
        return w[:-1]
    return w

NOUN_CATEGORY_MAP = {
    # Apparel & Wearables
    "hoodie": "apparel", "kurta": "apparel", "saree": "apparel", "shawl": "apparel", 
    "stole": "apparel", "dupatta": "apparel", "dress": "apparel", "jacket": "apparel",
    "shirt": "apparel", "pant": "apparel", "chappal": "footwear", "sandal": "footwear",
    "shoe": "footwear", "footwear": "footwear", "clothing": "apparel", "garment": "apparel",
    
    # Jewelry & Ornaments
    "ring": "jewelry", "bangle": "jewelry", "necklace": "jewelry", "anklet": "jewelry", 
    "earring": "jewelry", "pendant": "jewelry", "ornament": "jewelry", "jewel": "jewelry",
    "bracelet": "jewelry", "chain": "jewelry", "nacklace": "jewelry",
    
    # Home Decor & Furnishing
    "curtain": "homedecor", "rug": "homedecor", "carpet": "homedecor", "vase": "homedecor", 
    "plate": "homedecor", "diya": "homedecor", "lamp": "homedecor", "coaster": "homedecor",
    "pot": "homedecor", "craft": "homedecor", "statue": "homedecor", "bedsheet": "homedecor",
    "cushion": "homedecor", "pillow": "homedecor", "cover": "homedecor", "showpiece": "homedecor",
    
    # Food & Agriculture
    "mango": "produce", "alphonso": "produce", "spice": "produce", "saffron": "produce", 
    "tea": "produce", "fruit": "produce", "food": "produce", "grain": "produce", "rice": "produce"
}

FOOD_FRUIT_KEYWORDS = {"mango", "alphonso", "kesar", "fruit", "spice", "saffron", "rice", "tea", "food"}
FOOD_FRUIT_CATEGORIES = {"agricultural products", "food & beverages", "organic produce"}

class DatabaseService:
    @staticmethod
    def get_supabase_client() -> Client:
        return get_supabase_client()

    @staticmethod
    def get_products(query: str = None, category: str = None, region: str = None, seller_id: str = None):
        client = get_supabase_client()
        try:
            tbl = client.table("seller_products").select("*, seller_profiles!inner(business_name, verification_status, craft_certification, active)").eq("active", True)
            if seller_id:
                tbl = tbl.eq("seller_id", seller_id)
            else:
                tbl = tbl.eq("seller_profiles.active", True)

            res = tbl.execute()
            products = res.data if res.data else []
        except Exception as e:
            try:
                tbl = client.table("seller_products").select("*").eq("active", True)
                if seller_id:
                    tbl = tbl.eq("seller_id", seller_id)
                res = tbl.execute()
                products = res.data if res.data else []
            except Exception:
                products = []

        if seller_id and products:
            # Filter strictly for this seller ID in case inner join didn't filter
            products = [p for p in products if str(p.get("seller_id")) == str(seller_id)]

        if query and products:
            q_clean = str(query).lower().strip()
            stop_words = {"need", "procure", "want", "buy", "source", "units", "pcs", "pieces", "days", "delivery", "within", "for", "with", "from", "and", "the", "just", "find", "live", "pune", "maharashtra", "next", "in"}
            raw_tokens = [w for w in re.findall(r'\w+', q_clean) if len(w) > 2 and w not in stop_words]
            if not raw_tokens:
                raw_tokens = [q_clean]

            stemmed_tokens = [stem_word(w) for w in raw_tokens]

            # Identify target core product nouns in user query
            core_nouns = [t for t in stemmed_tokens if t in NOUN_CATEGORY_MAP or any(t.startswith(k) or k in t for k in NOUN_CATEGORY_MAP)]

            scored = []
            for p in products:
                name = str(p.get("name", "")).lower()
                desc = str(p.get("description", "")).lower()
                cat = str(p.get("category", "")).lower()
                reg = str(p.get("region", "")).lower()
                tags = [str(t).lower() for t in p.get("tags", [])]
                s_name = str(p.get("seller_name", "")).lower()

                name_stemmed_words = [stem_word(w) for w in re.findall(r'\w+', name)]

                score = 0
                matched_noun = False

                for t, t_stem in zip(raw_tokens, stemmed_tokens):
                    # Check exact or stemmed word match in product name
                    if t_stem in name_stemmed_words or t in name or t_stem in name:
                        score += 50
                        if any(t_stem in cn or cn in t_stem for cn in core_nouns):
                            matched_noun = True
                            score += 50
                    elif any(t_stem in str(tg) for tg in tags):
                        score += 25
                        if any(t_stem in cn or cn in t_stem for cn in core_nouns):
                            matched_noun = True
                            score += 25
                    elif t_stem in desc or t in desc:
                        score += 10
                    elif t_stem in cat or t in cat:
                        score += 15

                # Food & Agricultural Category Boost
                if any(fk in q_clean for fk in FOOD_FRUIT_KEYWORDS) and cat in FOOD_FRUIT_CATEGORIES:
                    score += 100
                    matched_noun = True

                # CRITICAL STRICT GROUNDING: If user query contains explicit core nouns (like hoodie, saree, mango, ring),
                # product MUST match at least one core noun!
                if core_nouns and not matched_noun:
                    score = -999

                if score > 0:
                    scored.append((score, p))

            # Sort candidate products by semantic match score (highest score first)
            scored.sort(key=lambda x: x[0], reverse=True)
            if scored:
                top_score = scored[0][0]
                filtered = [item[1] for item in scored if item[0] >= (top_score * 0.70)]
                return filtered

            return []

        return products

    @staticmethod
    def get_sellers(active_only: bool = True):
        client = get_supabase_client()
        try:
            query = client.table("seller_profiles").select("*")
            if active_only:
                query = query.eq("active", True)
            res = query.execute()
            return res.data if res.data else []
        except Exception as e:
            return []

    @staticmethod
    def add_product(product_data: dict):
        client = get_supabase_client()
        try:
            res = client.table("seller_products").insert(product_data).execute()
            return {"success": True, "product": res.data[0] if res.data else product_data}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def update_product_full(product_id: str, update_data: dict):
        client = get_supabase_client()
        try:
            payload = {
                "name": update_data.get("name"),
                "description": update_data.get("description"),
                "category": update_data.get("category"),
                "region": update_data.get("region"),
                "price": float(update_data.get("price", 0)),
                "available_stock": int(update_data.get("available_stock", 0)),
            }
            img = update_data.get("image_url")
            if img:
                payload["image_url"] = img
                payload["image_urls"] = [img]

            res = client.table("seller_products").update(payload).eq("id", product_id).execute()
            return {"success": True, "product": res.data[0] if res.data else payload}
        except Exception as e:
            print("Product update primary attempt notice:", e)
            try:
                fallback_payload = {
                    "name": update_data.get("name"),
                    "description": update_data.get("description"),
                    "category": update_data.get("category"),
                    "region": update_data.get("region"),
                    "price": float(update_data.get("price", 0)),
                    "available_stock": int(update_data.get("available_stock", 0)),
                }
                res = client.table("seller_products").update(fallback_payload).eq("id", product_id).execute()
                return {"success": True, "product": res.data[0] if res.data else fallback_payload}
            except Exception as e2:
                return {"success": False, "error": str(e2)}

    @staticmethod
    def delete_product(product_id: str):
        client = get_supabase_client()
        try:
            client.table("seller_products").update({"active": False}).eq("id", product_id).execute()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def update_order_status(result_id: str, new_status: str):
        client = get_supabase_client()
        try:
            client.table("procurement_results").update({"status": new_status}).eq("id", result_id).execute()
            return {"success": True, "status": new_status}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def get_seller_analytics(seller_business_name: str = None, seller_id: str = None):
        client = get_supabase_client()
        analytics = {
            "inquiries_count": 0,
            "total_sourced_value": 0.0,
            "delivered_orders_count": 0,
            "delivered_sourced_value": 0.0,
            "pending_orders_count": 0,
            "not_accepted_count": 0,
            "delivery_success_rate": 0.0,
            "active_products_count": 0,
            "orders": []
        }

        if seller_id:
            try:
                prods_res = client.table("seller_products").select("id").eq("seller_id", seller_id).eq("active", True).execute()
                analytics["active_products_count"] = len(prods_res.data) if prods_res.data else 0
            except Exception:
                pass

        if seller_business_name:
            try:
                res = client.table("procurement_results").select("*, procurement_requests(raw_prompt, destination)").eq("supplier_name", seller_business_name).order("created_at", desc=True).execute()
                if res.data:
                    orders = []
                    delivered_count = 0
                    delivered_val = 0.0
                    pending_count = 0
                    not_accepted_count = 0

                    for item in res.data:
                        raw_req = item.get("procurement_requests") or {}
                        order_status = item.get("status") or "Pending"
                        total_cost = float(item.get("total_cost") or 0.0)

                        if order_status == "Stock Delivered":
                            delivered_count += 1
                            delivered_val += total_cost
                        elif order_status in ["Not Accepted", "Cancelled"]:
                            not_accepted_count += 1
                        else:
                            pending_count += 1

                        orders.append({
                            "id": item["id"],
                            "createdAt": item["created_at"],
                            "rawPrompt": raw_req.get("raw_prompt") or f"Order for {item['quantity']} units",
                            "productName": item["product_name"],
                            "quantity": item["quantity"],
                            "totalCost": total_cost,
                            "deliveryDays": item["delivery_days"],
                            "riskLevel": item["risk_level"],
                            "status": order_status,
                            "destination": raw_req.get("destination") or "International"
                        })

                    total_orders = len(orders)
                    analytics["orders"] = orders
                    analytics["inquiries_count"] = total_orders
                    analytics["total_sourced_value"] = sum(o["totalCost"] for o in orders)
                    analytics["delivered_orders_count"] = delivered_count
                    analytics["delivered_sourced_value"] = delivered_val
                    analytics["pending_orders_count"] = pending_count
                    analytics["not_accepted_count"] = not_accepted_count
                    if total_orders > 0:
                        analytics["delivery_success_rate"] = round((delivered_count / total_orders) * 100, 1)
            except Exception as e:
                print("Analytics query notice:", e)

        return analytics

    @staticmethod
    def get_admin_analytics():
        client = get_supabase_client()
        analytics = {
            "is_admin": True,
            "total_products_count": 0,
            "total_sellers_count": 0,
            "inquiries_count": 0,
            "total_sourced_value": 0.0,
            "delivered_orders_count": 0,
            "delivered_sourced_value": 0.0,
            "pending_orders_count": 0,
            "top_selling_sellers": [],
            "orders": []
        }

        try:
            sellers = client.table("seller_profiles").select("*").execute()
            analytics["total_sellers_count"] = len(sellers.data) if sellers.data else 0

            prods = client.table("seller_products").select("*").eq("active", True).execute()
            analytics["total_products_count"] = len(prods.data) if prods.data else 0

            res = client.table("procurement_results").select("*, procurement_requests(raw_prompt, destination)").order("created_at", desc=True).execute()
            if res.data:
                orders = []
                delivered_count = 0
                delivered_val = 0.0
                pending_count = 0

                seller_stats = {}

                for item in res.data:
                    raw_req = item.get("procurement_requests") or {}
                    order_status = item.get("status") or "Pending"
                    total_cost = float(item.get("total_cost") or 0.0)
                    s_name = item.get("supplier_name", "Artisan Seller")

                    if s_name not in seller_stats:
                        seller_stats[s_name] = {"seller_name": s_name, "total_orders": 0, "total_value": 0.0, "delivered_orders": 0}

                    seller_stats[s_name]["total_orders"] += 1
                    seller_stats[s_name]["total_value"] += total_cost

                    if order_status == "Stock Delivered":
                        delivered_count += 1
                        delivered_val += total_cost
                        seller_stats[s_name]["delivered_orders"] += 1
                    else:
                        pending_count += 1

                    orders.append({
                        "id": item["id"],
                        "createdAt": item["created_at"],
                        "rawPrompt": raw_req.get("raw_prompt") or f"Order for {item['quantity']} units",
                        "supplierName": s_name,
                        "productName": item["product_name"],
                        "quantity": item["quantity"],
                        "totalCost": total_cost,
                        "deliveryDays": item["delivery_days"],
                        "riskLevel": item["risk_level"],
                        "status": order_status,
                        "destination": raw_req.get("destination") or "International"
                    })

                analytics["orders"] = orders
                analytics["inquiries_count"] = len(orders)
                analytics["total_sourced_value"] = sum(o["totalCost"] for o in orders)
                analytics["delivered_orders_count"] = delivered_count
                analytics["delivered_sourced_value"] = delivered_val
                analytics["pending_orders_count"] = pending_count

                # Sort sellers by total revenue & order volume
                sorted_sellers = sorted(seller_stats.values(), key=lambda x: x["total_value"], reverse=True)
                analytics["top_selling_sellers"] = sorted_sellers
        except Exception as e:
            print("Admin analytics query notice:", e)

        return analytics

    @staticmethod
    def save_procurement_run(req_prompt, result_data, user_id=None):
        client = get_supabase_client()
        try:
            req_res = client.table("procurement_requests").insert({
                "user_id": user_id,
                "raw_prompt": req_prompt,
                "product_type": result_data.get("product_name", "Handicraft"),
                "quantity": result_data.get("quantity", 50),
                "status": "completed"
            }).execute()

            req_id = req_res.data[0]["id"] if req_res.data else None

            client.table("procurement_results").insert({
                "request_id": req_id,
                "user_id": user_id,
                "supplier_name": result_data.get("supplier_name", "Artisan Guild"),
                "product_name": result_data.get("product_name", "Handicraft Item"),
                "quantity": result_data.get("quantity", 50),
                "product_cost": result_data.get("product_cost", 100000),
                "shipping_cost": result_data.get("shipping_cost", 0),
                "total_cost": result_data.get("total_cost", 100000),
                "delivery_days": result_data.get("delivery_days", 8),
                "risk_level": result_data.get("risk_level", "LOW"),
                "carbon_kg": result_data.get("carbon_kg", 10.0),
                "status": "Pending",
                "selected_route": result_data.get("selected_route", {}),
                "reasons": result_data.get("reasons", []),
                "alternatives": result_data.get("alternatives", []),
                "workflow_logs": result_data.get("workflow_logs", [])
            }).execute()
        except Exception as e:
            print("Supabase save run notice:", e)

    @staticmethod
    def get_procurement_history(user_id=None):
        client = get_supabase_client()
        try:
            query = client.table("procurement_results").select("*, procurement_requests(raw_prompt, destination)").order("created_at", desc=True)
            if user_id:
                query = query.eq("user_id", user_id)
            res = query.execute()
            if res.data:
                history = []
                for item in res.data:
                    raw_req = item.get("procurement_requests") or {}
                    history.append({
                        "id": item["id"],
                        "createdAt": item["created_at"],
                        "rawPrompt": raw_req.get("raw_prompt") or f"Order for {item['quantity']} units of {item['product_name']}",
                        "supplierName": item["supplier_name"],
                        "productName": item["product_name"],
                        "quantity": item["quantity"],
                        "totalCost": float(item["total_cost"]),
                        "deliveryDays": item["delivery_days"],
                        "riskLevel": item["risk_level"],
                        "status": item.get("status") or "Pending",
                        "destination": raw_req.get("destination") or "International",
                        "carbonKg": float(item.get("carbon_kg") or 0.0)
                    })
                return history
        except Exception as e:
            pass
        return []

    @staticmethod
    def update_stock(product_id: str, new_stock: int):
        client = get_supabase_client()
        try:
            client.table("seller_products").update({"available_stock": new_stock}).eq("id", product_id).execute()
            return {"success": True, "availableStock": new_stock}
        except Exception as e:
            return {"success": False, "error": str(e)}
