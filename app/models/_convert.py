"""Tiny conversion helpers shared by models.

CSV stores everything as strings, so models own the string<->typed conversion.
"""
from __future__ import annotations

import json


def to_int(value, default=None):
    if value is None or value == "":
        return default
    return int(value)


def to_float(value, default=None):
    if value is None or value == "":
        return default
    return float(value)


def to_json(value, default):
    if value is None or value == "":
        return default
    if isinstance(value, (dict, list)):
        return value
    return json.loads(value)


def dump_json(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)
