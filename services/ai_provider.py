"""
BharatLink Nexus AI — Centralized AI Provider Service
Supports Google Gemini (Official Google Gen AI SDK) with Developer API & Vertex AI modes,
and Groq as a configurable secondary provider.
Includes rate limiting, retries, structured JSON validation, and audit tracking.
"""

import os
import re
import json
import time
import logging
from typing import Dict, Any, Optional, List, Tuple
from pydantic import BaseModel

from config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    AI_PROVIDER,
    GOOGLE_GENAI_USE_VERTEXAI,
    GOOGLE_CLOUD_PROJECT,
    GOOGLE_CLOUD_LOCATION,
    GROQ_API_KEY,
    GROQ_MODEL
)

logger = logging.getLogger("BharatLink.AIProvider")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [AIProvider] %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Global test mock store
_MOCK_RESPONSES: Dict[str, Any] = {}
_MOCK_ENABLED: bool = False

def set_mock_mode(enabled: bool, mock_responses: Optional[Dict[str, Any]] = None):
    """Enable or disable deterministic mock mode for automated test suites."""
    global _MOCK_ENABLED, _MOCK_RESPONSES
    _MOCK_ENABLED = enabled
    if mock_responses:
        _MOCK_RESPONSES = mock_responses
    elif not enabled:
        _MOCK_RESPONSES = {}

class AIResult(BaseModel):
    content: str
    parsed_json: Optional[Any] = None
    provider: str
    model: str
    latency_ms: float
    success: bool
    error: Optional[str] = None

class AIProviderService:
    @staticmethod
    def _sanitize_log_message(msg: str) -> str:
        """Strip any accidental key exposure from log messages."""
        clean = msg
        if GEMINI_API_KEY and len(GEMINI_API_KEY) > 6:
            clean = clean.replace(GEMINI_API_KEY, "[REDACTED_GEMINI_KEY]")
        if GROQ_API_KEY and len(GROQ_API_KEY) > 6:
            clean = clean.replace(GROQ_API_KEY, "[REDACTED_GROQ_KEY]")
        return clean

    @staticmethod
    def _extract_json(text: str) -> Optional[Any]:
        """Robustly extracts JSON from an LLM response string."""
        if not text:
            return None
        text = text.strip()
        # 1. Try direct parsing
        try:
            return json.loads(text)
        except Exception:
            pass

        # 2. Try markdown fenced ```json ... ```
        fence_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text, re.IGNORECASE)
        if fence_match:
            try:
                return json.loads(fence_match.group(1).strip())
            except Exception:
                pass

        # 3. Try finding outermost object { ... } or array [ ... ]
        obj_match = re.search(r'(\{[\s\S]*\})', text)
        if obj_match:
            try:
                return json.loads(obj_match.group(1))
            except Exception:
                pass

        arr_match = re.search(r'(\[[\s\S]*\])', text)
        if arr_match:
            try:
                return json.loads(arr_match.group(1))
            except Exception:
                pass

        return None

    @classmethod
    def invoke_gemini(
        cls,
        prompt: str,
        system_instruction: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature: float = 0.2,
        max_retries: int = 2
    ) -> AIResult:
        """
        Invokes Google Gemini via the official google.genai SDK.
        Supports both Developer API mode (GEMINI_API_KEY) and Vertex AI mode.
        """
        target_model = model_name or GEMINI_MODEL or "gemini-3.5-flash"
        start_time = time.time()

        if _MOCK_ENABLED:
            mock_val = _MOCK_RESPONSES.get("gemini", _MOCK_RESPONSES.get("default", "{\"mock\": true}"))
            parsed = cls._extract_json(str(mock_val))
            return AIResult(
                content=str(mock_val),
                parsed_json=parsed,
                provider="gemini_mock",
                model=target_model,
                latency_ms=(time.time() - start_time) * 1000,
                success=True
            )

        try:
            from google import genai
            from google.genai import types
        except ImportError as e:
            return AIResult(
                content="",
                provider="gemini",
                model=target_model,
                latency_ms=(time.time() - start_time) * 1000,
                success=False,
                error=f"google-genai SDK not installed: {e}"
            )

        client = None
        try:
            if GOOGLE_GENAI_USE_VERTEXAI and GOOGLE_CLOUD_PROJECT:
                client = genai.Client(
                    vertexai=True,
                    project=GOOGLE_CLOUD_PROJECT,
                    location=GOOGLE_CLOUD_LOCATION
                )
            elif GEMINI_API_KEY:
                client = genai.Client(api_key=GEMINI_API_KEY)
            else:
                # Attempt default credentials via ADC
                client = genai.Client()
        except Exception as e:
            err_msg = cls._sanitize_log_message(str(e))
            logger.error(f"Failed to initialize Google Gen AI Client: {err_msg}")
            return AIResult(
                content="",
                provider="gemini",
                model=target_model,
                latency_ms=(time.time() - start_time) * 1000,
                success=False,
                error=f"Gemini client initialization error: {err_msg}"
            )

        # Build combined prompt or config with system instruction
        config = types.GenerateContentConfig(
            temperature=temperature,
            system_instruction=system_instruction if system_instruction else None
        )

        last_error = None
        active_model = target_model

        for attempt in range(max_retries + 1):
            try:
                resp = client.models.generate_content(
                    model=active_model,
                    contents=prompt,
                    config=config
                )
                text = resp.text or ""
                latency = (time.time() - start_time) * 1000
                parsed = cls._extract_json(text)
                return AIResult(
                    content=text,
                    parsed_json=parsed,
                    provider="gemini",
                    model=active_model,
                    latency_ms=latency,
                    success=True
                )
            except Exception as e:
                err_str = str(e)
                last_error = err_str

                # Handle model deprecation/404 specifically
                if ("404" in err_str or "NOT_FOUND" in err_str):
                    if "gemini-2.5-flash" in active_model:
                        logger.warning("gemini-2.5-flash unavailable for current API tier. Upgrading request to gemini-3.5-flash...")
                        active_model = "gemini-3.5-flash"
                        continue
                    elif "gemini-3.5-flash" in active_model:
                        logger.warning("Switching to gemini-3.5-flash-lite...")
                        active_model = "gemini-3.5-flash-lite"
                        continue

                # Handle transient 503 / 429
                if attempt < max_retries and ("503" in err_str or "429" in err_str or "UNAVAILABLE" in err_str or "RESOURCE_EXHAUSTED" in err_str):
                    if "gemini-3.5-flash" in active_model:
                        active_model = "gemini-3.5-flash-lite"
                    backoff = (2 ** attempt) * 0.75
                    time.sleep(backoff)
                    continue
                break

        clean_err = cls._sanitize_log_message(str(last_error))
        logger.error(f"Gemini invocation failed on model {active_model}: {clean_err}")
        return AIResult(
            content="",
            provider="gemini",
            model=active_model,
            latency_ms=(time.time() - start_time) * 1000,
            success=False,
            error=clean_err
        )

    @classmethod
    def invoke_groq(
        cls,
        prompt: str,
        system_instruction: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature: float = 0.2
    ) -> AIResult:
        """
        Invokes Groq via langchain_groq as a secondary/specialized provider.
        """
        target_model = model_name or GROQ_MODEL or "openai/gpt-oss-20b"
        start_time = time.time()

        if _MOCK_ENABLED:
            mock_val = _MOCK_RESPONSES.get("groq", _MOCK_RESPONSES.get("default", "{\"mock\": true}"))
            parsed = cls._extract_json(str(mock_val))
            return AIResult(
                content=str(mock_val),
                parsed_json=parsed,
                provider="groq_mock",
                model=target_model,
                latency_ms=(time.time() - start_time) * 1000,
                success=True
            )

        if not GROQ_API_KEY:
            return AIResult(
                content="",
                provider="groq",
                model=target_model,
                latency_ms=(time.time() - start_time) * 1000,
                success=False,
                error="GROQ_API_KEY is not configured."
            )

        try:
            from langchain_groq import ChatGroq
            llm = ChatGroq(
                groq_api_key=GROQ_API_KEY,
                model_name=target_model,
                temperature=temperature,
                timeout=12.0
            )

            messages = []
            if system_instruction:
                messages.append({"role": "system", "content": system_instruction})
            messages.append({"role": "user", "content": prompt})

            resp = llm.invoke(messages)
            text = str(resp.content) if hasattr(resp, "content") else str(resp)
            latency = (time.time() - start_time) * 1000
            parsed = cls._extract_json(text)

            return AIResult(
                content=text,
                parsed_json=parsed,
                provider="groq",
                model=target_model,
                latency_ms=latency,
                success=True
            )
        except Exception as e:
            clean_err = cls._sanitize_log_message(str(e))
            logger.error(f"Groq invocation failed on model {target_model}: {clean_err}")
            return AIResult(
                content="",
                provider="groq",
                model=target_model,
                latency_ms=(time.time() - start_time) * 1000,
                success=False,
                error=clean_err
            )

    @classmethod
    def generate(
        cls,
        prompt: str,
        system_instruction: Optional[str] = None,
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature: float = 0.2
    ) -> AIResult:
        """
        Unified entrypoint for AI operations.
        Selects provider based on parameter or global AI_PROVIDER setting.
        Never silently lies about which provider or model answered.
        """
        selected_provider = (provider or AI_PROVIDER or "gemini").lower().strip()

        if selected_provider == "groq":
            return cls.invoke_groq(
                prompt=prompt,
                system_instruction=system_instruction,
                model_name=model_name,
                temperature=temperature
            )
        else:
            res = cls.invoke_gemini(
                prompt=prompt,
                system_instruction=system_instruction,
                model_name=model_name,
                temperature=temperature
            )
            # Resilient fallback to secondary provider (Groq) if Gemini encounters quota, 503, or rate limits
            if not res.success and GROQ_API_KEY:
                logger.warning(
                    f"Gemini primary provider returned error: {res.error or 'unknown'}. "
                    "Transparently activating Groq secondary provider (llama-3.3-70b-versatile)..."
                )
                groq_res = cls.invoke_groq(
                    prompt=prompt,
                    system_instruction=system_instruction,
                    temperature=temperature
                )
                if groq_res.success:
                    return groq_res
            return res

    @classmethod
    def generate_json(
        cls,
        prompt: str,
        system_instruction: Optional[str] = None,
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature: float = 0.1
    ) -> Tuple[Optional[Any], AIResult]:
        """
        Convenience wrapper ensuring structured JSON extraction.
        Returns a tuple of (parsed_json, full_result).
        """
        sys_prompt = (system_instruction or "") + "\nRespond with valid, parseable JSON only. Do not wrap in commentary."
        result = cls.generate(
            prompt=prompt,
            system_instruction=sys_prompt,
            provider=provider,
            model_name=model_name,
            temperature=temperature
        )
        return result.parsed_json, result
