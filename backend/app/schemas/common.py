from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class Envelope(BaseModel, Generic[T]):
    """Standard response envelope — `ok=True` with `data` or `ok=False` with `error`."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    ok: bool = True
    data: T | None = None
    warnings: list[str] = []
    error: dict[str, Any] | None = None


def ok(data: Any, warnings: list[str] | None = None) -> dict[str, Any]:
    return {"ok": True, "data": data, "warnings": warnings or [], "error": None}


def err(code: str, message: str, *, details: dict | None = None, status: int = 400) -> dict[str, Any]:
    return {
        "ok": False,
        "data": None,
        "warnings": [],
        "error": {"code": code, "message": message, "details": details or {}, "status": status},
    }
