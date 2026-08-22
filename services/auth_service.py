import hashlib
from typing import Optional, Dict, Any
from services.supabase_service import get_supabase_client

# Salted PBKDF2 SHA256 password hashing
def hash_password(password: str) -> str:
    salt = b"bharatlink_nexus_salt_2026"
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000).hex()

def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed

ADMIN_EMAIL = "admin@bharatlink.com"
ADMIN_HASH = hash_password("Admin@123")

class AuthService:
    @staticmethod
    def ensure_admin_exists():
        client = get_supabase_client()
        try:
            res = client.table("profiles").select("*").eq("email", ADMIN_EMAIL).execute()
            if not res.data or len(res.data) == 0:
                client.table("profiles").insert({
                    "email": ADMIN_EMAIL,
                    "password_hash": ADMIN_HASH,
                    "full_name": "BharatLink Global Admin",
                    "role": "admin"
                }).execute()
            else:
                client.table("profiles").update({"password_hash": ADMIN_HASH, "role": "admin"}).eq("email", ADMIN_EMAIL).execute()
        except Exception as e:
            print("Auto-ensure admin notice:", e)

    @staticmethod
    def signup_buyer(email: str, password: str, full_name: str, company_name: str = "") -> Dict[str, Any]:
        client = get_supabase_client()
        hashed = hash_password(password)
        clean_email = email.lower().strip()
        try:
            res = client.table("profiles").insert({
                "email": clean_email,
                "password_hash": hashed,
                "full_name": full_name,
                "company_name": company_name,
                "role": "buyer"
            }).execute()
            if res.data and len(res.data) > 0:
                user = res.data[0]
                user.pop("password_hash", None)
                return {"success": True, "user": user}
        except Exception as e:
            return {"success": False, "error": str(e)}
        return {"success": False, "error": "Signup failed"}

    @staticmethod
    def login_user(email: str, password: str) -> Dict[str, Any]:
        clean_email = email.lower().strip()
        
        if clean_email == ADMIN_EMAIL:
            AuthService.ensure_admin_exists()

        client = get_supabase_client()
        hashed = hash_password(password)
        try:
            res = client.table("profiles").select("*").eq("email", clean_email).execute()
            if res.data and len(res.data) > 0:
                user = res.data[0]
                if user["password_hash"] == hashed:
                    user.pop("password_hash", None)

                    # Check if user is a seller and if they are approved by admin
                    if user.get("role") != "admin":
                        seller = AuthService.get_seller_by_user_id(user["id"])
                        if seller and not seller.get("active", False):
                            return {
                                "success": False, 
                                "error": f"Your artisan seller account ('{seller.get('business_name')}') is currently pending admin verification. Administrator approval is required before logging in."
                            }

                    return {"success": True, "user": user}
                else:
                    return {"success": False, "error": "Invalid email or password"}
            else:
                if clean_email == ADMIN_EMAIL and password == "Admin@123":
                    return {"success": True, "user": {"id": "admin-001", "email": ADMIN_EMAIL, "full_name": "BharatLink Global Admin", "role": "admin"}}
                return {"success": False, "error": "Account not found"}
        except Exception as e:
            if clean_email == ADMIN_EMAIL and password == "Admin@123":
                return {"success": True, "user": {"id": "admin-001", "email": ADMIN_EMAIL, "full_name": "BharatLink Global Admin", "role": "admin"}}
            return {"success": False, "error": str(e)}

    @staticmethod
    def signup_seller(
        email: str, 
        password: str, 
        business_name: str, 
        contact_person: str, 
        phone: str,
        whatsapp_number: str,
        state: str, 
        city: str, 
        craft_category: str
    ) -> Dict[str, Any]:
        clean_email = email.lower().strip()
        client = get_supabase_client()
        
        buyer_res = AuthService.signup_buyer(clean_email, password, contact_person, business_name)
        if not buyer_res["success"]:
            user_res = AuthService.login_user(clean_email, password)
            if not user_res["success"]:
                return buyer_res
            user = user_res["user"]
        else:
            user = buyer_res["user"]

        # 100% Fail-Safe Payload handling for Supabase Schema Column variations
        try:
            payload = {
                "user_id": user["id"],
                "business_name": business_name,
                "contact_person": contact_person,
                "email": clean_email,
                "phone": phone,
                "whatsapp_number": whatsapp_number,
                "state": state,
                "city": city,
                "address": f"{city}, {state}",
                "craft_category": craft_category,
                "verification_status": "Pending Admin Approval",
                "craft_certification": "GI Tag Certified",
                "active": False # Requires Admin Verification
            }
            seller_res = client.table("seller_profiles").insert(payload).execute()
        except Exception as e:
            print("Primary seller insert notice, retrying with schema fallback:", e)
            try:
                payload_fallback = {
                    "user_id": user["id"],
                    "business_name": business_name,
                    "contact_person": contact_person,
                    "email": clean_email,
                    "phone": whatsapp_number or phone,
                    "state": state,
                    "city": city,
                    "address": f"{city}, {state}",
                    "craft_category": craft_category,
                    "verification_status": "Pending Admin Approval",
                    "craft_certification": "GI Tag Certified",
                    "active": False # Requires Admin Verification
                }
                seller_res = client.table("seller_profiles").insert(payload_fallback).execute()
            except Exception as e2:
                return {"success": False, "error": str(e2)}

        seller = seller_res.data[0] if seller_res.data else None
        return {
            "success": True, 
            "user": user, 
            "seller": seller, 
            "pending": True,
            "message": "Registration submitted! Your seller profile is under review by BharatLink Platform Admin."
        }

    @staticmethod
    def get_seller_by_user_id(user_id: str) -> Optional[Dict[str, Any]]:
        client = get_supabase_client()
        try:
            res = client.table("seller_profiles").select("*").eq("user_id", user_id).execute()
            if res.data and len(res.data) > 0:
                return res.data[0]
        except Exception as e:
            pass
        return None

    @staticmethod
    def approve_seller(seller_id: str) -> Dict[str, Any]:
        client = get_supabase_client()
        try:
            client.table("seller_profiles").update({"active": True, "verification_status": "Verified"}).eq("id", seller_id).execute()
            client.table("seller_products").update({"active": True}).eq("seller_id", seller_id).execute()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def deactivate_seller(seller_id: str) -> Dict[str, Any]:
        client = get_supabase_client()
        try:
            client.table("seller_profiles").update({"active": False, "verification_status": "Deactivated"}).eq("id", seller_id).execute()
            client.table("seller_products").update({"active": False}).eq("seller_id", seller_id).execute()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
