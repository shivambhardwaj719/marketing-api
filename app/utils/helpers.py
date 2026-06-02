from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def utcnow() -> datetime:
    return datetime.now(UTC)


def strip_act_prefix(account_id: str) -> str:
    return account_id.replace("act_", "")


def extract_lead_field(field_data: list[dict[str, Any]], name: str) -> str | None:
    for field in field_data:
        if field.get("name") == name:
            values = field.get("values", [])
            return values[0] if values else None
    return None


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
