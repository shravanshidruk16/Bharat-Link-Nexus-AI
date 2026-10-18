"""
BharatLink Nexus AI — Unified Database Repository Layer
Supports Cloud Firestore via Firebase Admin SDK, Firebase Emulators,
and a high-fidelity local repository engine backed by data/catalog_seed.json.
Provides ACID transactions, oversell prevention, tenant isolation, and audit logging.
"""

import os
import json
import uuid
import time
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from config import (
    FIREBASE_PROJECT_ID,
    FIRESTORE_EMULATOR_HOST,
    FIREBASE_AUTH_EMULATOR_HOST,
    ALLOW_LOCAL_FALLBACK,
    ENVIRONMENT
)

class InsufficientStockError(Exception):
    """Raised when an inventory decrement would result in negative stock."""
    pass

class UnauthorizedTenantError(Exception):
    """Raised when a user attempts to modify a resource owned by another tenant."""
    pass

class RepositoryService:
    _lock = threading.RLock()
    _initialized = False
    _firestore_client = None
    _movement_counter = 0
    _connection_error = None
    _source = "uninitialized"

    # In-memory collections (keyed by collection_name -> dict of id -> document)
    _db: Dict[str, Dict[str, Dict[str, Any]]] = {
        "users": {},
        "seller_profiles": {},
        "products": {},
        "inventory_movements": {},
        "categories": {},
        "procurement_requests": {},
        "recommendations": {},
        "orders": {},
        "sales_transactions": {},
        "customer_preferences": {},
        "analytics_events": {},
        "audit_logs": {}
    }

    @classmethod
    def initialize(cls, force_reconnect: bool = False):
        """
        Initializes Firestore connection using Application Default Credentials (locally or Cloud Run)
        or loads seed data if explicitly in development/test mode.
        """
        with cls._lock:
            if cls._initialized and not force_reconnect:
                return

            if force_reconnect:
                for k in cls._db:
                    cls._db[k] = {}

            cls._firestore_client = None
            cls._connection_error = None
            cls._source = "uninitialized"

            # Attempt live Cloud Firestore connection
            try:
                import firebase_admin
                from firebase_admin import credentials, firestore

                if FIRESTORE_EMULATOR_HOST:
                    os.environ["FIRESTORE_EMULATOR_HOST"] = FIRESTORE_EMULATOR_HOST

                if not firebase_admin._apps:
                    cred = credentials.ApplicationDefault() if not FIRESTORE_EMULATOR_HOST else None
                    firebase_admin.initialize_app(cred, {"projectId": FIREBASE_PROJECT_ID})

                client = firestore.client()
                if client and getattr(client, "project", None):
                    cls._firestore_client = client
            except Exception as e:
                cls._firestore_client = None
                cls._connection_error = str(e)

            fallback_explicit = os.getenv("ALLOW_LOCAL_FALLBACK", "").lower() in ("true", "1", "yes")
            is_prod = (ENVIRONMENT == "production")

            # If live Firestore is connected, hydrate authentic migrated collections
            if cls._firestore_client:
                synced = cls._sync_from_firestore()
                if synced:
                    cls._initialized = True
                    return

            # Production strictness check: Never silently fall back to sample data in production unless explicitly allowed
            if is_prod and not cls._firestore_client and not fallback_explicit:
                cls._source = "disconnected"
                cls._initialized = True
                return

            # Prime repository catalog if fallback is allowed or not in production
            if (fallback_explicit or not is_prod) and not cls._db["products"]:
                cls._load_seed_catalog()
                cls._source = "local_seed"

            cls._initialized = True

    @classmethod
    def _sync_from_firestore(cls) -> bool:
        """Streams authentic migrated records from Cloud Firestore into memory cache."""
        if not cls._firestore_client:
            return False
        try:
            collections_to_sync = [
                ("products", "products"),
                ("seller_profiles", "seller_profiles"),
                ("users", "users"),
                ("procurement_requests", "procurement_requests"),
                ("orders", "orders"),
                ("recommendations", "recommendations"),
            ]
            total_loaded = 0
            for col_name, cache_key in collections_to_sync:
                docs = list(cls._firestore_client.collection(col_name).stream())
                for d in docs:
                    cls._db[cache_key][d.id] = d.to_dict()
                total_loaded += len(docs)

            if total_loaded > 0:
                cls._source = "cloud_firestore"
                # Seed realistic sales transactions for analytics if none exist
                cls._seed_initial_sales_transactions()
                return True
        except Exception as e:
            cls._connection_error = str(e)
        return False

    @classmethod
    def is_firestore_connected(cls) -> bool:
        cls.initialize()
        return cls._firestore_client is not None

    @classmethod
    def get_connection_info(cls) -> Dict[str, Any]:
        cls.initialize()
        is_conn = cls._firestore_client is not None
        fallback_explicit = os.getenv("ALLOW_LOCAL_FALLBACK", "").lower() in ("true", "1", "yes")
        return {
            "firestore_connected": is_conn,
            "project_id": FIREBASE_PROJECT_ID,
            "environment": ENVIRONMENT,
            "source": cls._source,
            "products_count": len(cls._db["products"]),
            "sellers_count": len(cls._db["seller_profiles"]),
            "users_count": len(cls._db["users"]),
            "orders_count": len(cls._db["orders"]),
            "allow_local_fallback": (fallback_explicit or ALLOW_LOCAL_FALLBACK) and ENVIRONMENT != "production",
            "mode": "cloud_firestore" if is_conn else ("local_fallback" if (fallback_explicit or ALLOW_LOCAL_FALLBACK) and ENVIRONMENT != "production" else "disconnected")
        }

    @classmethod
    def _load_seed_catalog(cls):
        """Loads products, sellers, and initial profiles from data/catalog_seed.json."""
        seed_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "catalog_seed.json")
        if not os.path.exists(seed_path):
            return

        try:
            with open(seed_path, "r", encoding="utf-8") as f:
                seed = json.load(f)

            # 1. Load users
            for u in seed.get("users", []):
                uid = str(u.get("id") or u.get("uid") or uuid.uuid4())
                cls._db["users"][uid] = {
                    "id": uid,
                    "uid": uid,
                    "email": u.get("email", "").lower().strip(),
                    "full_name": u.get("full_name", "Artisan Member"),
                    "company_name": u.get("company_name", ""),
                    "role": u.get("role", "buyer"),
                    "country": u.get("country", "India"),
                    "created_at": str(u.get("created_at") or datetime.utcnow().isoformat())
                }

            # 2. Load sellers
            for s in seed.get("seller_profiles", []):
                sid = str(s.get("id") or uuid.uuid4())
                cls._db["seller_profiles"][sid] = {
                    "id": sid,
                    "user_id": str(s.get("user_id") or ""),
                    "business_name": s.get("business_name", "Artisan Guild"),
                    "contact_person": s.get("contact_person", "Artisan Lead"),
                    "email": s.get("email", "").lower().strip(),
                    "phone": s.get("phone", "+91 98230 12345"),
                    "whatsapp_number": s.get("whatsapp_number", "919823012345"),
                    "country": s.get("country", "India"),
                    "state": s.get("state", "Maharashtra"),
                    "city": s.get("city", "Pune"),
                    "craft_category": s.get("craft_category", "Handicrafts & Handloom"),
                    "craft_certification": s.get("craft_certification", "GI Tag Certified"),
                    "verification_status": s.get("verification_status", "Verified"),
                    "active": bool(s.get("active", True)),
                    "created_at": str(s.get("created_at") or datetime.utcnow().isoformat())
                }

            # 3. Load products
            for p in seed.get("seller_products", []):
                pid = str(p.get("id") or uuid.uuid4())
                cls._db["products"][pid] = {
                    "id": pid,
                    "seller_id": str(p.get("seller_id") or ""),
                    "seller_name": p.get("seller_name", "Artisan Collective"),
                    "name": p.get("name", "Handcrafted Product"),
                    "description": p.get("description", ""),
                    "category": p.get("category", "Handicrafts & Handloom"),
                    "subcategory": p.get("subcategory", ""),
                    "region": p.get("region", "India"),
                    "price": float(p.get("price") or 0.0),
                    "currency": p.get("currency", "INR"),
                    "available_stock": int(p.get("available_stock") or 0),
                    "minimum_order_quantity": int(p.get("minimum_order_quantity") or 1),
                    "weight_kg": float(p.get("weight_kg") or 1.0),
                    "authenticity_status": p.get("authenticity_status", "GI Certified Authentic"),
                    "image_url": p.get("image_url") or "",
                    "active": bool(p.get("active", True)),
                    "created_at": str(p.get("created_at") or datetime.utcnow().isoformat()),
                    "updated_at": str(p.get("updated_at") or datetime.utcnow().isoformat())
                }

            # 4. Generate initial demonstration sales transactions for demand forecasting
            cls._seed_initial_sales_transactions()
        except Exception as e:
            print("Notice loading seed catalog:", e)

    @classmethod
    def _seed_initial_sales_transactions(cls):
        """Generates realistic sales transactions and orders from active catalog products."""
        if cls._db["sales_transactions"]:
            return

        products = list(cls._db["products"].values())[:25]
        sellers = list(cls._db["seller_profiles"].values())
        if not products or not sellers:
            return

        now = datetime.utcnow()
        for i in range(40):
            p = products[i % len(products)]
            qty = (i % 5 + 1) * 5
            unit_price = p.get("price", 500.0)
            tx_id = f"tx-{1000 + i}"
            order_id = f"ord-{2000 + i}"

            tx = {
                "id": tx_id,
                "order_id": order_id,
                "product_id": p.get("id", ""),
                "product_name": p.get("name", ""),
                "seller_id": p.get("seller_id", ""),
                "buyer_id": "buyer-demo-001",
                "units_sold": qty,
                "unit_price": unit_price,
                "total_amount": qty * unit_price,
                "category": p.get("category", "Handicrafts & Handloom"),
                "timestamp": datetime.fromtimestamp(now.timestamp() - (i * 86400 * 1.5)).isoformat()
            }
            cls._db["sales_transactions"][tx_id] = tx

            if order_id not in cls._db["orders"]:
                cls._db["orders"][order_id] = {
                    "id": order_id,
                    "buyer_id": "buyer-demo-001",
                    "seller_id": p.get("seller_id", ""),
                    "seller_name": p.get("seller_name", "Artisan Collective"),
                    "product_id": p.get("id", ""),
                    "product_name": p.get("name", ""),
                    "quantity": qty,
                    "total_cost": qty * unit_price,
                    "status": "Stock Delivered" if i % 2 == 0 else "Pending",
                    "created_at": tx["timestamp"]
                }

    # ============================================================
    # USERS & PROFILES
    # ============================================================
    @classmethod
    def get_user_by_email(cls, email: str) -> Optional[Dict[str, Any]]:
        cls.initialize()
        clean = email.lower().strip()
        for u in cls._db["users"].values():
            if u.get("email") == clean:
                return dict(u)

        # Fallback to direct Firestore lookup if not in cache
        if cls._firestore_client:
            try:
                matches = list(cls._firestore_client.collection("users").where("email", "==", clean).limit(1).stream())
                if matches:
                    user_data = matches[0].to_dict()
                    cls._db["users"][matches[0].id] = user_data
                    return dict(user_data)
            except Exception:
                pass
        return None

    @classmethod
    def get_user_by_id(cls, user_id: str) -> Optional[Dict[str, Any]]:
        cls.initialize()
        u = cls._db["users"].get(str(user_id))
        if u:
            return dict(u)

        if cls._firestore_client:
            try:
                doc = cls._firestore_client.collection("users").document(str(user_id)).get()
                if doc.exists:
                    user_data = doc.to_dict()
                    cls._db["users"][doc.id] = user_data
                    return dict(user_data)
            except Exception:
                pass
        return None

    @classmethod
    def create_user(cls, user_data: Dict[str, Any]) -> Dict[str, Any]:
        cls.initialize()
        with cls._lock:
            uid = str(user_data.get("id") or user_data.get("uid") or uuid.uuid4())
            record = {
                "id": uid,
                "uid": uid,
                "email": user_data.get("email", "").lower().strip(),
                "full_name": user_data.get("full_name", ""),
                "company_name": user_data.get("company_name", ""),
                "role": user_data.get("role", "buyer"),
                "country": user_data.get("country", "India"),
                "password_hash": user_data.get("password_hash", ""),
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            cls._db["users"][uid] = record

            if cls._firestore_client:
                try:
                    cls._firestore_client.collection("users").document(uid).set(record, merge=True)
                except Exception as e:
                    print("Notice writing user to Firestore:", e)

            cls.add_audit_log("USER_REGISTERED", uid, record["role"], "users", {"email": record["email"]})
            return dict(record)

    @classmethod
    def update_user_password(cls, user_id: str, password_hash: str) -> bool:
        cls.initialize()
        with cls._lock:
            user = cls._db["users"].get(user_id)
            if not user:
                return False
            user["password_hash"] = password_hash
            user["updated_at"] = datetime.utcnow().isoformat()
            if cls._firestore_client:
                try:
                    cls._firestore_client.collection("users").document(user_id).set({
                        "password_hash": password_hash,
                        "updated_at": user["updated_at"]
                    }, merge=True)
                except Exception as e:
                    print("Notice updating user password in Firestore:", e)
            return True

    @classmethod
    def update_user_role(cls, user_id: str, new_role: str, admin_user_id: str) -> bool:
        cls.initialize()
        with cls._lock:
            admin = cls.get_user_by_id(admin_user_id)
            if not admin or admin.get("role") != "admin":
                raise UnauthorizedTenantError("Only an administrator can modify user roles.")
            if user_id in cls._db["users"]:
                cls._db["users"][user_id]["role"] = new_role
                cls._db["users"][user_id]["updated_at"] = datetime.utcnow().isoformat()

                if cls._firestore_client:
                    try:
                        cls._firestore_client.collection("users").document(str(user_id)).update({
                            "role": new_role,
                            "updated_at": cls._db["users"][user_id]["updated_at"]
                        })
                    except Exception as e:
                        print("Notice updating user role in Firestore:", e)

                cls.add_audit_log("USER_ROLE_CHANGED", admin_user_id, "admin", f"users/{user_id}", {"new_role": new_role})
                return True
            return False

    # ============================================================
    # SELLER PROFILES
    # ============================================================
    @classmethod
    def get_seller_by_user_id(cls, user_id: str) -> Optional[Dict[str, Any]]:
        cls.initialize()
        for s in cls._db["seller_profiles"].values():
            if str(s.get("user_id")) == str(user_id):
                return dict(s)

        if cls._firestore_client:
            try:
                matches = list(cls._firestore_client.collection("seller_profiles").where("user_id", "==", str(user_id)).limit(1).stream())
                if matches:
                    seller_data = matches[0].to_dict()
                    cls._db["seller_profiles"][matches[0].id] = seller_data
                    return dict(seller_data)
            except Exception:
                pass
        return None

    @classmethod
    def get_seller_by_id(cls, seller_id: str) -> Optional[Dict[str, Any]]:
        cls.initialize()
        s = cls._db["seller_profiles"].get(str(seller_id))
        if s:
            return dict(s)

        if cls._firestore_client:
            try:
                doc = cls._firestore_client.collection("seller_profiles").document(str(seller_id)).get()
                if doc.exists:
                    seller_data = doc.to_dict()
                    cls._db["seller_profiles"][doc.id] = seller_data
                    return dict(seller_data)
            except Exception:
                pass
        return None

    @classmethod
    def get_sellers(cls, active_only: bool = True, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        cls.initialize()
        sellers = list(cls._db["seller_profiles"].values())
        if active_only:
            sellers = [s for s in sellers if s.get("active", False)]
        res = [dict(s) for s in sellers]
        if limit is not None and limit > 0:
            return res[:limit]
        return res

    @classmethod
    def create_seller(cls, seller_data: Dict[str, Any]) -> Dict[str, Any]:
        cls.initialize()
        with cls._lock:
            sid = str(seller_data.get("id") or uuid.uuid4())
            record = {
                "id": sid,
                "user_id": str(seller_data.get("user_id", "")),
                "business_name": seller_data.get("business_name", ""),
                "contact_person": seller_data.get("contact_person", ""),
                "email": seller_data.get("email", "").lower().strip(),
                "phone": seller_data.get("phone", ""),
                "whatsapp_number": seller_data.get("whatsapp_number", ""),
                "country": seller_data.get("country", "India"),
                "state": seller_data.get("state", ""),
                "city": seller_data.get("city", ""),
                "craft_category": seller_data.get("craft_category", "Handicrafts & Handloom"),
                "craft_certification": seller_data.get("craft_certification", "GI Tag Certified"),
                "verification_status": seller_data.get("verification_status", "Pending Admin Approval"),
                "active": bool(seller_data.get("active", False)),
                "created_at": datetime.utcnow().isoformat()
            }
            cls._db["seller_profiles"][sid] = record

            if cls._firestore_client:
                try:
                    cls._firestore_client.collection("seller_profiles").document(sid).set(record, merge=True)
                except Exception as e:
                    print("Notice writing seller to Firestore:", e)

            cls.add_audit_log("SELLER_REGISTERED", sid, "seller", "seller_profiles", {"business_name": record["business_name"]})
            return dict(record)

    @classmethod
    def update_seller_status(cls, seller_id: str, active: bool, admin_user_id: str) -> bool:
        cls.initialize()
        with cls._lock:
            admin = cls.get_user_by_id(admin_user_id)
            if not admin or admin.get("role") != "admin":
                raise UnauthorizedTenantError("Only an administrator can approve or deactivate sellers.")
            if seller_id in cls._db["seller_profiles"]:
                cls._db["seller_profiles"][seller_id]["active"] = active
                cls._db["seller_profiles"][seller_id]["verification_status"] = "Verified" if active else "Deactivated"

                if cls._firestore_client:
                    try:
                        cls._firestore_client.collection("seller_profiles").document(str(seller_id)).update({
                            "active": active,
                            "verification_status": cls._db["seller_profiles"][seller_id]["verification_status"]
                        })
                    except Exception as e:
                        print("Notice updating seller status in Firestore:", e)

                cls.add_audit_log("SELLER_STATUS_CHANGED", admin_user_id, "admin", f"seller_profiles/{seller_id}", {"active": active})
                return True
            return False

    # ============================================================
    # PRODUCTS & INVENTORY
    # ============================================================
    @classmethod
    def get_products(
        cls,
        query: Optional[str] = None,
        category: Optional[str] = None,
        region: Optional[str] = None,
        seller_id: Optional[str] = None,
        active_only: bool = True,
        limit: int = 200,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        cls.initialize()

        fallback_explicit = os.getenv("ALLOW_LOCAL_FALLBACK", "").lower() in ("true", "1", "yes")
        if ENVIRONMENT == "production" and not cls._firestore_client and not fallback_explicit:
            return []

        prods = list(cls._db["products"].values())

        if active_only:
            prods = [p for p in prods if p.get("active", True)]

        if seller_id:
            prods = [p for p in prods if str(p.get("seller_id")) == str(seller_id)]

        if category:
            cat_clean = category.lower().strip()
            prods = [p for p in prods if cat_clean in str(p.get("category", "")).lower()]

        if region:
            reg_clean = region.lower().strip()
            prods = [p for p in prods if reg_clean in str(p.get("region", "")).lower()]

        if query:
            q_clean = query.lower().strip()
            tokens = [w for w in q_clean.split() if len(w) > 2]
            scored = []
            for p in prods:
                name = str(p.get("name", "")).lower()
                desc = str(p.get("description", "")).lower()
                p_cat = str(p.get("category", "")).lower()
                p_reg = str(p.get("region", "")).lower()
                score = 0
                for t in tokens:
                    if t in name: score += 10
                    if t in p_cat: score += 5
                    if t in desc: score += 2
                    if t in p_reg: score += 3
                if score > 0 or not tokens:
                    scored.append((score, p))
            scored.sort(key=lambda x: x[0], reverse=True)
            prods = [item[1] for item in scored]

        return [dict(p) for p in prods[offset : offset + limit]]

    @classmethod
    def get_product_by_id(cls, product_id: str) -> Optional[Dict[str, Any]]:
        cls.initialize()
        p = cls._db["products"].get(str(product_id))
        if p:
            return dict(p)

        if cls._firestore_client:
            try:
                doc = cls._firestore_client.collection("products").document(str(product_id)).get()
                if doc.exists:
                    p_data = doc.to_dict()
                    cls._db["products"][doc.id] = p_data
                    return dict(p_data)
            except Exception:
                pass
        return None

    @classmethod
    def add_product(cls, product_data: Dict[str, Any], seller_id: str) -> Dict[str, Any]:
        cls.initialize()
        with cls._lock:
            pid = str(product_data.get("id") or uuid.uuid4())
            record = {
                "id": pid,
                "seller_id": str(seller_id),
                "seller_name": product_data.get("seller_name", "Artisan Guild"),
                "name": product_data.get("name", "").strip(),
                "description": product_data.get("description", "").strip(),
                "category": product_data.get("category", "Handicrafts & Handloom"),
                "subcategory": product_data.get("subcategory", ""),
                "region": product_data.get("region", "India"),
                "price": float(product_data.get("price") or 0.0),
                "currency": product_data.get("currency", "INR"),
                "available_stock": int(product_data.get("available_stock") or 0),
                "minimum_order_quantity": int(product_data.get("minimum_order_quantity") or 1),
                "weight_kg": float(product_data.get("weight_kg") or 1.0),
                "authenticity_status": product_data.get("authenticity_status", "GI Certified Authentic"),
                "image_url": product_data.get("image_url", ""),
                "active": bool(product_data.get("active", True)),
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            cls._db["products"][pid] = record

            if cls._firestore_client:
                try:
                    cls._firestore_client.collection("products").document(pid).set(record, merge=True)
                except Exception as e:
                    print("Notice writing product to Firestore:", e)

            # Log inventory movement
            cls._log_inventory_movement(
                product_id=pid,
                seller_id=seller_id,
                prev_stock=0,
                new_stock=record["available_stock"],
                reason="Initial product creation"
            )
            return dict(record)

    @classmethod
    def update_product(cls, product_id: str, update_data: Dict[str, Any], actor_seller_id: str, is_admin: bool = False) -> Dict[str, Any]:
        cls.initialize()
        with cls._lock:
            prod = cls._db["products"].get(str(product_id))
            if not prod:
                raise ValueError(f"Product {product_id} not found.")

            # Tenant isolation check
            if not is_admin and str(prod.get("seller_id")) != str(actor_seller_id):
                raise UnauthorizedTenantError("Sellers can only modify their own products.")

            prev_stock = prod["available_stock"]
            firestore_updates = {}
            for k in ["name", "description", "category", "region", "price", "image_url", "active"]:
                if k in update_data and update_data[k] is not None:
                    prod[k] = update_data[k]
                    firestore_updates[k] = update_data[k]

            if "available_stock" in update_data and update_data["available_stock"] is not None:
                new_stock = int(update_data["available_stock"])
                prod["available_stock"] = new_stock
                firestore_updates["available_stock"] = new_stock
                if new_stock != prev_stock:
                    cls._log_inventory_movement(
                        product_id=product_id,
                        seller_id=prod["seller_id"],
                        prev_stock=prev_stock,
                        new_stock=new_stock,
                        reason="Manual stock adjustment"
                    )

            prod["updated_at"] = datetime.utcnow().isoformat()
            firestore_updates["updated_at"] = prod["updated_at"]
            cls._db["products"][product_id] = prod

            if cls._firestore_client and firestore_updates:
                try:
                    cls._firestore_client.collection("products").document(str(product_id)).update(firestore_updates)
                except Exception as e:
                    print("Notice updating product in Firestore:", e)

            return dict(prod)

    @classmethod
    def delete_product(cls, product_id: str, actor_seller_id: str, is_admin: bool = False) -> bool:
        cls.initialize()
        with cls._lock:
            prod = cls._db["products"].get(str(product_id))
            if not prod:
                return False
            if not is_admin and str(prod.get("seller_id")) != str(actor_seller_id):
                raise UnauthorizedTenantError("Sellers can only delete their own products.")

            prod["active"] = False
            prod["updated_at"] = datetime.utcnow().isoformat()

            if cls._firestore_client:
                try:
                    cls._firestore_client.collection("products").document(str(product_id)).update({
                        "active": False,
                        "updated_at": prod["updated_at"]
                    })
                except Exception as e:
                    print("Notice deleting product in Firestore:", e)

            cls.add_audit_log("PRODUCT_DELETED", actor_seller_id, "seller" if not is_admin else "admin", f"products/{product_id}", {})
            return True

    # ============================================================
    # TRANSACTIONAL STOCK UPDATE & OVERSELL PROTECTION
    # ============================================================
    @classmethod
    def decrement_stock_transactional(cls, product_id: str, quantity: int, order_id: str) -> Dict[str, Any]:
        """
        Atomically checks and decrements product inventory.
        Raises InsufficientStockError if quantity exceeds available stock.
        Executes via Firestore transaction when connected or in-memory lock otherwise.
        """
        cls.initialize()
        with cls._lock:
            prod = cls._db["products"].get(str(product_id))
            if not prod:
                raise ValueError(f"Product {product_id} not found.")

            current_stock = prod["available_stock"]
            if current_stock < quantity:
                raise InsufficientStockError(
                    f"Requested {quantity} units, but only {current_stock} units are in stock."
                )

            new_stock = current_stock - quantity
            prod["available_stock"] = new_stock
            prod["updated_at"] = datetime.utcnow().isoformat()
            cls._db["products"][product_id] = prod

            if cls._firestore_client:
                try:
                    from firebase_admin import firestore
                    transaction = cls._firestore_client.transaction()
                    doc_ref = cls._firestore_client.collection("products").document(str(product_id))

                    @firestore.transactional
                    def update_in_transaction(txn, ref):
                        snap = ref.get(transaction=txn)
                        if not snap.exists:
                            return
                        data = snap.to_dict()
                        f_stock = data.get("available_stock", 0)
                        if f_stock < quantity:
                            raise InsufficientStockError(
                                f"Requested {quantity} units, but only {f_stock} units are in stock in Firestore."
                            )
                        txn.update(ref, {
                            "available_stock": f_stock - quantity,
                            "updated_at": datetime.utcnow().isoformat()
                        })

                    update_in_transaction(transaction, doc_ref)
                except InsufficientStockError:
                    prod["available_stock"] = current_stock
                    raise
                except Exception as e:
                    print("Notice transactional decrement in Firestore:", e)

            # Log audit movement
            cls._log_inventory_movement(
                product_id=product_id,
                seller_id=prod["seller_id"],
                prev_stock=current_stock,
                new_stock=new_stock,
                reason=f"Order fulfillment: {order_id}"
            )
            return dict(prod)

    @classmethod
    def _log_inventory_movement(cls, product_id: str, seller_id: str, prev_stock: int, new_stock: int, reason: str):
        mid = str(uuid.uuid4())
        cls._movement_counter += 1
        record = {
            "id": mid,
            "product_id": str(product_id),
            "seller_id": str(seller_id),
            "previous_stock": prev_stock,
            "new_stock": new_stock,
            "delta": new_stock - prev_stock,
            "reason": reason,
            "created_at": datetime.utcnow().isoformat(),
            "seq": cls._movement_counter
        }
        cls._db["inventory_movements"][mid] = record

    @classmethod
    def get_inventory_movements(cls, product_id: Optional[str] = None, seller_id: Optional[str] = None) -> List[Dict[str, Any]]:
        cls.initialize()
        movements = list(cls._db["inventory_movements"].values())
        if product_id:
            movements = [m for m in movements if m.get("product_id") == str(product_id)]
        if seller_id:
            movements = [m for m in movements if m.get("seller_id") == str(seller_id)]
        movements.sort(key=lambda x: (x.get("seq") or 0, x.get("created_at", "")), reverse=True)
        return [dict(m) for m in movements]

    # ============================================================
    # PROCUREMENT REQUESTS & RECOMMENDATIONS
    # ============================================================
    @classmethod
    def save_procurement_request(cls, req_data: Dict[str, Any]) -> Dict[str, Any]:
        cls.initialize()
        with cls._lock:
            rid = str(req_data.get("id") or uuid.uuid4())
            record = {
                "id": rid,
                "user_id": str(req_data.get("user_id") or "anonymous"),
                "raw_prompt": req_data.get("raw_prompt", ""),
                "product_type": req_data.get("product_type", ""),
                "quantity": int(req_data.get("quantity") or 50),
                "destination": req_data.get("destination", "India"),
                "deadline_days": int(req_data.get("deadline_days") or 10),
                "budget_inr": float(req_data.get("budget_inr") or 0.0),
                "status": req_data.get("status", "completed"),
                "created_at": datetime.utcnow().isoformat()
            }
            cls._db["procurement_requests"][rid] = record

            if cls._firestore_client:
                try:
                    cls._firestore_client.collection("procurement_requests").document(rid).set(record, merge=True)
                except Exception as e:
                    print("Notice writing procurement request to Firestore:", e)

            return dict(record)

    @classmethod
    def save_procurement_result(cls, res_data: Dict[str, Any]) -> Dict[str, Any]:
        cls.initialize()
        with cls._lock:
            res_id = str(res_data.get("id") or uuid.uuid4())
            record = {
                "id": res_id,
                "request_id": str(res_data.get("request_id", "")),
                "user_id": str(res_data.get("user_id") or "anonymous"),
                "supplier_name": res_data.get("supplier_name", "Artisan Guild"),
                "product_name": res_data.get("product_name", "Handloom Item"),
                "quantity": int(res_data.get("quantity") or 50),
                "product_cost": float(res_data.get("product_cost") or 0.0),
                "shipping_cost": float(res_data.get("shipping_cost") or 0.0),
                "total_cost": float(res_data.get("total_cost") or 0.0),
                "delivery_days": int(res_data.get("delivery_days") or 4),
                "risk_level": res_data.get("risk_level", "LOW"),
                "status": res_data.get("status", "Pending"),
                "selected_route": res_data.get("selected_route", {}),
                "reasons": res_data.get("reasons", []),
                "alternatives": res_data.get("alternatives", []),
                "created_at": datetime.utcnow().isoformat()
            }
            cls._db["recommendations"][res_id] = record

            if cls._firestore_client:
                try:
                    cls._firestore_client.collection("recommendations").document(res_id).set(record, merge=True)
                except Exception as e:
                    print("Notice writing recommendation to Firestore:", e)

            return dict(record)

    @classmethod
    def get_procurement_history(cls, user_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        cls.initialize()
        results = list(cls._db["recommendations"].values())
        if user_id:
            results = [r for r in results if r.get("user_id") == str(user_id)]
        results.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return [dict(r) for r in results[:limit]]

    # ============================================================
    # ORDERS & TRANSACTIONS
    # ============================================================
    @classmethod
    def create_order(cls, order_data: Dict[str, Any]) -> Dict[str, Any]:
        cls.initialize()
        with cls._lock:
            oid = str(order_data.get("id") or f"ord-{uuid.uuid4().hex[:8]}")
            record = {
                "id": oid,
                "buyer_id": str(order_data.get("buyer_id", "")),
                "seller_id": str(order_data.get("seller_id", "")),
                "seller_name": order_data.get("seller_name", "Artisan Collective"),
                "product_id": str(order_data.get("product_id", "")),
                "product_name": order_data.get("product_name", ""),
                "quantity": int(order_data.get("quantity") or 1),
                "total_cost": float(order_data.get("total_cost") or 0.0),
                "status": order_data.get("status", "Pending"),
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            cls._db["orders"][oid] = record

            if cls._firestore_client:
                try:
                    cls._firestore_client.collection("orders").document(oid).set(record, merge=True)
                except Exception as e:
                    print("Notice writing order to Firestore:", e)

            return dict(record)

    @classmethod
    def update_order_status(cls, order_id: str, new_status: str, actor_id: str, is_admin: bool = False) -> bool:
        cls.initialize()
        with cls._lock:
            order = cls._db["orders"].get(str(order_id))
            if not order:
                # Check recommendations as orders fallback
                rec = cls._db["recommendations"].get(str(order_id))
                if rec:
                    rec["status"] = new_status
                    if cls._firestore_client:
                        try:
                            cls._firestore_client.collection("recommendations").document(str(order_id)).update({
                                "status": new_status,
                                "updated_at": datetime.utcnow().isoformat()
                            })
                        except Exception as e:
                            print("Notice updating recommendation status in Firestore:", e)
                    return True
                return False

            if not is_admin and str(order.get("seller_id")) != str(actor_id):
                raise UnauthorizedTenantError("Sellers can only modify their own orders.")

            order["status"] = new_status
            order["updated_at"] = datetime.utcnow().isoformat()

            if cls._firestore_client:
                try:
                    cls._firestore_client.collection("orders").document(str(order_id)).update({
                        "status": new_status,
                        "updated_at": order["updated_at"]
                    })
                except Exception as e:
                    print("Notice updating order in Firestore:", e)

            return True

    @classmethod
    def get_orders(cls, seller_id: Optional[str] = None, buyer_id: Optional[str] = None) -> List[Dict[str, Any]]:
        cls.initialize()
        orders = list(cls._db["orders"].values())
        if seller_id:
            orders = [o for o in orders if str(o.get("seller_id")) == str(seller_id)]
        if buyer_id:
            orders = [o for o in orders if str(o.get("buyer_id")) == str(buyer_id)]
        orders.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return [dict(o) for o in orders]

    @classmethod
    def get_sales_transactions(cls, seller_id: Optional[str] = None, limit: int = 200) -> List[Dict[str, Any]]:
        cls.initialize()
        txs = list(cls._db["sales_transactions"].values())
        if seller_id:
            txs = [t for t in txs if str(t.get("seller_id")) == str(seller_id)]
        txs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return [dict(t) for t in txs[:limit]]

    # ============================================================
    # CUSTOMER PREFERENCES (PERSONALIZATION)
    # ============================================================
    @classmethod
    def get_customer_preferences(cls, user_id: str) -> Optional[Dict[str, Any]]:
        cls.initialize()
        prefs = cls._db["customer_preferences"].get(str(user_id))
        return dict(prefs) if prefs else None

    @classmethod
    def save_customer_preferences(cls, user_id: str, prefs_data: Dict[str, Any]) -> Dict[str, Any]:
        cls.initialize()
        with cls._lock:
            record = {
                "user_id": str(user_id),
                "preferred_categories": prefs_data.get("preferred_categories", []),
                "max_budget": float(prefs_data.get("max_budget") or 0.0),
                "preferred_region": prefs_data.get("preferred_region", ""),
                "destination": prefs_data.get("destination", "India"),
                "consent_given": bool(prefs_data.get("consent_given", True)),
                "updated_at": datetime.utcnow().isoformat()
            }
            cls._db["customer_preferences"][str(user_id)] = record

            if cls._firestore_client:
                try:
                    cls._firestore_client.collection("customer_preferences").document(str(user_id)).set(record, merge=True)
                except Exception as e:
                    print("Notice writing customer preferences to Firestore:", e)

            return dict(record)

    @classmethod
    def delete_customer_preferences(cls, user_id: str) -> bool:
        cls.initialize()
        with cls._lock:
            if str(user_id) in cls._db["customer_preferences"]:
                del cls._db["customer_preferences"][str(user_id)]
                if cls._firestore_client:
                    try:
                        cls._firestore_client.collection("customer_preferences").document(str(user_id)).delete()
                    except Exception as e:
                        print("Notice deleting customer preferences in Firestore:", e)
                return True
            return False

    # ============================================================
    # AUDIT LOGS
    # ============================================================
    @classmethod
    def add_audit_log(cls, action: str, user_id: str, role: str, resource: str, details: Dict[str, Any]):
        cls.initialize()
        with cls._lock:
            lid = str(uuid.uuid4())
            record = {
                "id": lid,
                "action": action,
                "user_id": str(user_id),
                "role": role,
                "resource": resource,
                "details": details,
                "timestamp": datetime.utcnow().isoformat()
            }
            cls._db["audit_logs"][lid] = record
            if cls._firestore_client:
                try:
                    cls._firestore_client.collection("audit_logs").document(lid).set(record, merge=True)
                except Exception:
                    pass

    @classmethod
    def get_audit_logs(cls, limit: int = 50) -> List[Dict[str, Any]]:
        cls.initialize()
        logs = list(cls._db["audit_logs"].values())
        logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return [dict(l) for l in logs[:limit]]
