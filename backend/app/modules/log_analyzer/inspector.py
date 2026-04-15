"""Smart Debug Panel — state inspector.

Given a timestamp, collect everything the algo 'saw and did' at that tick:
  * positions (all products, latest at or before ts)
  * fills at the tick
  * sandbox log lines within ±N ticks (or ±N lines if ts absent)
  * cached quant metrics at that tick (microprice, wobi, z-score)
"""
from __future__ import annotations

from typing import Any

import polars as pl


def _latest_positions(positions: pl.LazyFrame, ts: int) -> dict[str, int]:
    if positions is None:
        return {}
    df = (
        positions.filter(pl.col("timestamp") <= ts)
        .sort(["product", "timestamp"])
        .group_by("product", maintain_order=True)
        .last()
        .collect()
    )
    if df.is_empty():
        return {}
    return {str(row["product"]): int(row["position"]) for row in df.to_dicts()}


def _fills_at(trades: pl.LazyFrame, ts: int) -> list[dict]:
    if trades is None:
        return []
    df = trades.filter(pl.col("timestamp") == ts).collect()
    return df.to_dicts() if not df.is_empty() else []


def _sandbox_window(sandbox: pl.LazyFrame, ts: int, *, radius_ticks: int = 5, radius_lines: int = 20) -> list[dict]:
    if sandbox is None:
        return []
    # Prefer timestamp-aware window when available; otherwise ±N lines.
    df = sandbox.collect()
    if df.is_empty():
        return []

    with_ts = df.filter(pl.col("timestamp").is_not_null())
    if not with_ts.is_empty():
        # Guess tick spacing = 100 (Prosperity default) so we don't shrink the
        # window if no lines fall in the exact ±N tick range.
        span = radius_ticks * 100
        win = df.filter(pl.col("timestamp").is_between(ts - span, ts + span))
        if not win.is_empty():
            return win.sort(["timestamp", "line_no"]).to_dicts()

    # Fallback: ±radius_lines around the closest line.
    closest_idx = (df["line_no"] - (df["line_no"].median() or 0)).abs().arg_min() or 0
    lo = max(0, closest_idx - radius_lines)
    hi = min(df.height, closest_idx + radius_lines + 1)
    return df.slice(lo, hi - lo).sort("line_no").to_dicts()


def inspect(
    *,
    positions: pl.LazyFrame | None,
    trades: pl.LazyFrame | None,
    sandbox: pl.LazyFrame | None,
    activities: pl.LazyFrame | None,
    ts: int,
) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    if activities is not None:
        df = activities.filter(pl.col("timestamp") == ts).collect()
        if not df.is_empty():
            metrics = {
                row["product"]: {
                    "mid_price": row["mid_price"],
                    "spread": (row["ask_price_1"] or 0) - (row["bid_price_1"] or 0),
                    "pnl": row["profit_and_loss"],
                }
                for row in df.to_dicts()
            }

    return {
        "timestamp": ts,
        "positions": _latest_positions(positions, ts) if positions is not None else {},
        "fills_at_tick": _fills_at(trades, ts) if trades is not None else [],
        "sandbox_window": _sandbox_window(sandbox, ts) if sandbox is not None else [],
        "metrics": metrics,
    }
