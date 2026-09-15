"""Application configuration and business-rule defaults."""
from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    DATA_DIR = str(BASE_DIR / "data")
    POLICY_DIR = str(BASE_DIR / "data_seed" / "policies")
    SECRET_KEY = "dev-not-secret"
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
