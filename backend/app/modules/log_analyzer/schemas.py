from __future__ import annotations

from pydantic import BaseModel, Field


class LogFilters(BaseModel):
    products: list[str] | None = None
    ts_range: tuple[int, int] | None = None


class DashboardRequest(BaseModel):
    filters: LogFilters = LogFilters()
    target_points: int = Field(default=8000, ge=100, le=200_000)


class CompareRequest(BaseModel):
    session_ids: list[str]
    filters: LogFilters = LogFilters()
    target_points: int = Field(default=8000, ge=100, le=200_000)


class SandboxQuery(BaseModel):
    q: str | None = None
    ts_from: int | None = None
    ts_to: int | None = None
    products: list[str] | None = None
    limit: int = Field(default=500, ge=1, le=5000)
    offset: int = Field(default=0, ge=0)
