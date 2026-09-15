"""Thin Gemini wrapper. Returns parsed JSON; callers fall back on any failure."""
from __future__ import annotations

import json
import os
import re
from typing import Any

from app.config import Config


class LLMService:
    def __init__(self):
        self.model = os.environ.get("GEMINI_MODEL") or Config.GEMINI_MODEL
        self.api_key = os.environ.get("GEMINI_API_KEY") or Config.GEMINI_API_KEY
        self._client = None

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def _client_or_none(self):
        if not self.available:
            return None
        if self._client is None:
            from google import genai

            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def complete_json(self, system: str, user: str) -> dict[str, Any] | None:
        """Ask Gemini Flash for a JSON object. Returns None on any failure."""
        client = self._client_or_none()
        if client is None:
            return None
        try:
            from google.genai import types

            response = client.models.generate_content(
                model=self.model,
                contents=user,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    temperature=0.2,
                    response_mime_type="application/json",
                ),
            )
            text = getattr(response, "text", None) or ""
            return _parse_json(text)
        except Exception:
            return None


def _parse_json(text: str) -> dict[str, Any] | None:
    raw = (text or "").strip()
    if not raw:
        return None
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None
