"""Shared helpers for the JSON API."""
from __future__ import annotations

from dataclasses import asdict, is_dataclass

from flask import current_app, request

from app.services.container import Services
from app.services.exceptions import ValidationError


def services() -> Services:
    return current_app.config["services"]


def body() -> dict:
    data = request.get_json(silent=True)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValidationError("request body must be a JSON object")
    return data


def require(data: dict, *fields: str) -> None:
    missing = [f for f in fields if data.get(f) in (None, "")]
    if missing:
        raise ValidationError(f"missing required field(s): {', '.join(missing)}")


def dump(obj):
    if isinstance(obj, list):
        return [dump(o) for o in obj]
    if isinstance(obj, dict):
        return {k: dump(v) for k, v in obj.items()}
    if is_dataclass(obj):
        return asdict(obj)
    return obj
