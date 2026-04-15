from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from threading import RLock
from typing import Any

import polars as pl

from app.core.errors import SessionNotFound


@dataclass
class MarketSession:
    """Holds cached LazyFrames for Module 1 (Market Data)."""

    session_id: str
    prices: pl.LazyFrame | None = None
    trades: pl.LazyFrame | None = None
    unified: pl.LazyFrame | None = None
    meta: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    touched_at: float = field(default_factory=time.time)


@dataclass
class LogSession:
    """Holds parsed sections for Module 2 (Submission Log Analyzer)."""

    session_id: str
    activities: pl.LazyFrame | None = None
    trade_history: pl.LazyFrame | None = None
    sandbox: pl.LazyFrame | None = None
    positions: pl.LazyFrame | None = None
    meta: dict[str, Any] = field(default_factory=dict)
    file_reports: list[dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    touched_at: float = field(default_factory=time.time)


class SessionStore:
    """Thread-safe in-memory store for both session types."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._market: dict[str, MarketSession] = {}
        self._logs: dict[str, LogSession] = {}

    # ---------- market ----------
    def new_market(self) -> MarketSession:
        sid = uuid.uuid4().hex
        s = MarketSession(session_id=sid)
        with self._lock:
            self._market[sid] = s
        return s

    def get_market(self, sid: str) -> MarketSession:
        with self._lock:
            s = self._market.get(sid)
            if s is None:
                raise SessionNotFound(f"market session {sid} not found")
            s.touched_at = time.time()
            return s

    # ---------- logs ----------
    def new_log(self) -> LogSession:
        sid = uuid.uuid4().hex
        s = LogSession(session_id=sid)
        with self._lock:
            self._logs[sid] = s
        return s

    def get_log(self, sid: str) -> LogSession:
        with self._lock:
            s = self._logs.get(sid)
            if s is None:
                raise SessionNotFound(f"log session {sid} not found")
            s.touched_at = time.time()
            return s


store = SessionStore()
