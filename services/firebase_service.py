"""
BharatLink Nexus AI — Firebase Authentication & Admin Service
Provides Firebase Admin SDK token verification, custom claims management,
and HMAC-signed session verification for secure browser sessions.
"""

import os
import hmac
import time
import json
import base64
import hashlib
import logging
from typing import Optional, Dict, Any

from config import (
    FIREBASE_PROJECT_ID,
    FIREBASE_AUTH_EMULATOR_HOST,
    SECRET_KEY
)

logger = logging.getLogger("BharatLink.FirebaseAuth")

_firebase_initialized = False

def init_firebase_admin():
    global _firebase_initialized
    if _firebase_initialized:
        return
    try:
        import firebase_admin
        from firebase_admin import credentials, auth

        if FIREBASE_AUTH_EMULATOR_HOST:
            os.environ["FIREBASE_AUTH_EMULATOR_HOST"] = FIREBASE_AUTH_EMULATOR_HOST

        if not firebase_admin._apps:
            cred = credentials.ApplicationDefault() if not FIREBASE_AUTH_EMULATOR_HOST else None
            firebase_admin.initialize_app(cred, {"projectId": FIREBASE_PROJECT_ID})
        _firebase_initialized = True
    except Exception as e:
        logger.warning(f"Firebase Admin SDK local init note: {e}")
        _firebase_initialized = False

class FirebaseAuthService:
    @staticmethod
    def verify_firebase_id_token(token: str) -> Optional[Dict[str, Any]]:
        """
        Verifies a Firebase ID token using the Firebase Admin SDK.
        Returns decoded claims or None if invalid/expired.
        """
        if not token:
            return None
        init_firebase_admin()
        try:
            from firebase_admin import auth
            decoded = auth.verify_id_token(token, check_revoked=True)
            return {
                "uid": decoded.get("uid"),
                "email": decoded.get("email"),
                "name": decoded.get("name") or decoded.get("email", "").split("@")[0],
                "role": decoded.get("role", "buyer"),
                "admin": decoded.get("admin", False) or (decoded.get("role") == "admin")
            }
        except Exception as e:
            logger.debug(f"Firebase ID token verification failed: {e}")
            return None

    @staticmethod
    def set_user_role(uid: str, role: str) -> bool:
        """Sets custom claims for role-based access control via Firebase Admin."""
        init_firebase_admin()
        try:
            from firebase_admin import auth
            auth.set_custom_user_claims(uid, {
                "role": role,
                "admin": (role == "admin")
            })
            return True
        except Exception as e:
            logger.error(f"Failed to set custom user claims for {uid}: {e}")
            return False

    # ============================================================
    # CRYPTOGRAPHICALLY SIGNED SESSION COOKIES (HMAC-SHA256)
    # Replaces insecure client-controlled unsigned JSON cookies!
    # ============================================================
    @staticmethod
    def create_signed_session(user_dict: Dict[str, Any], max_age_seconds: int = 7 * 86400) -> str:
        """
        Creates a tamper-proof signed session string with embedded expiration.
        Format: base64(payload_json).signature_hex
        """
        now_ts = int(time.time())
        clean_user = {
            "id": user_dict.get("id") or user_dict.get("uid"),
            "uid": user_dict.get("uid") or user_dict.get("id"),
            "email": user_dict.get("email", "").lower().strip(),
            "full_name": user_dict.get("full_name") or user_dict.get("name", "User"),
            "role": user_dict.get("role", "buyer"),
            "company_name": user_dict.get("company_name", ""),
            "seller_id": user_dict.get("seller_id"),
            "iat": now_ts,
            "exp": now_ts + max_age_seconds
        }
        raw_json = json.dumps(clean_user, separators=(',', ':'), sort_keys=True).encode("utf-8")
        payload_b64 = base64.urlsafe_b64encode(raw_json).decode("utf-8")
        signature = hmac.new(SECRET_KEY.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
        return f"{payload_b64}.{signature}"

    @staticmethod
    def verify_signed_session(session_str: str) -> Optional[Dict[str, Any]]:
        """
        Verifies the cryptographic signature and expiration of a session string.
        Returns payload dict if authentic and unexpired, or None if forged/expired.
        """
        if not session_str or "." not in session_str:
            return None
        parts = session_str.split(".", 1)
        if len(parts) != 2:
            return None

        payload_b64, signature = parts
        expected_sig = hmac.new(SECRET_KEY.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()

        # Constant-time comparison to prevent timing attacks
        if not hmac.compare_digest(signature, expected_sig):
            logger.warning("Tampered session signature detected! Rejecting request.")
            return None

        try:
            payload_json = base64.urlsafe_b64decode(payload_b64.encode("utf-8")).decode("utf-8")
            data = json.loads(payload_json)
            # Cryptographic expiration check
            if "exp" in data and isinstance(data["exp"], (int, float)):
                if time.time() > data["exp"]:
                    logger.warning("Session token has expired. Rejecting request.")
                    return None
            return data
        except Exception:
            return None
