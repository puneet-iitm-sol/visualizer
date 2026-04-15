"""Replay engine — produce a lightweight frame at a given timestamp, or step
to the next/previous tick.

The client drives playback (setInterval / requestAnimationFrame). This module
just answers "what did the algo see at ts=X?" cheaply.
"""
from __future__ import annotations

import bisect
from typing import Any

import polars as pl

from app.modules.log_analyzer.inspector import inspect


def timestamp_index(activities: pl.LazyFrame | None) -> list[int]:
    if activities is None:
        return []
    col = activities.select("timestamp").unique().sort("timestamp").collect()
    return col["timestamp"].to_list()


def step(
    *,
    index: list[int],
    current_ts: int | None,
    direction: int = 1,
) -> int | None:
    """Return the next (or previous) ts in `index` relative to `current_ts`."""
    if not index:
        return None
    if current_ts is None:
        return index[0] if direction >= 0 else index[-1]
    pos = bisect.bisect_left(index, current_ts)
    if direction >= 0:
        nxt = pos + 1 if pos < len(index) and index[pos] == current_ts else pos
        return index[nxt] if nxt < len(index) else None
    prv = pos - 1
    return index[prv] if prv >= 0 else None


def frame_at(
    *,
    activities: pl.LazyFrame | None,
    positions: pl.LazyFrame | None,
    trades: pl.LazyFrame | None,
    sandbox: pl.LazyFrame | None,
    ts: int,
) -> dict[str, Any]:
    state = inspect(
        positions=positions, trades=trades, sandbox=sandbox,
        activities=activities, ts=ts,
    )
    return {"ts": ts, **state}
