"""Multi-submission overlay + divergence diff.

Takes N log sessions and returns:
  * per-session cumulative PnL (aligned on union of timestamps)
  * per-session position curves per product
  * divergence rows — timestamps where any two sessions' positions differ
"""
from __future__ import annotations

from typing import Any

import polars as pl

from app.core.downsample import lttb
from app.core.session import LogSession


def _session_pnl(s: LogSession) -> pl.DataFrame:
    if s.activities is None:
        return pl.DataFrame(schema={"timestamp": pl.Int64, "product": pl.Utf8, "cum_pnl": pl.Float64})
    df = s.activities.sort(["product", "timestamp"]).collect()
    if df.is_empty():
        return pl.DataFrame(schema={"timestamp": pl.Int64, "product": pl.Utf8, "cum_pnl": pl.Float64})
    return df.with_columns(
        pl.col("profit_and_loss").cum_sum().over("product").alias("cum_pnl"),
        pl.col("product").cast(pl.Utf8),
    ).select(["timestamp", "product", "cum_pnl"])


def _session_positions(s: LogSession) -> pl.DataFrame:
    if s.positions is None:
        return pl.DataFrame(schema={"timestamp": pl.Int64, "product": pl.Utf8, "position": pl.Int32})
    return s.positions.collect().with_columns(pl.col("product").cast(pl.Utf8))


def compare(sessions: list[LogSession], *, target_points: int = 6000) -> dict[str, Any]:
    pnl_out: dict[str, Any] = {}
    pos_out: dict[str, dict[str, Any]] = {}

    # ---- PnL per session (sum across products) ----
    for s in sessions:
        pnl = _session_pnl(s)
        if pnl.is_empty():
            pnl_out[s.session_id] = {"x": [], "y": []}
            continue
        total = pnl.group_by("timestamp", maintain_order=True).agg(pl.col("cum_pnl").sum()).sort("timestamp")
        xs, ys = lttb(total["timestamp"], total["cum_pnl"].cast(pl.Float64), target_points)
        pnl_out[s.session_id] = {"x": xs.to_list(), "y": ys.to_list()}

    # ---- positions per (session, product) ----
    all_products: set[str] = set()
    session_positions: dict[str, pl.DataFrame] = {}
    for s in sessions:
        pdf = _session_positions(s)
        session_positions[s.session_id] = pdf
        if not pdf.is_empty():
            all_products.update(pdf["product"].to_list())

    for product in sorted(all_products):
        pos_out[product] = {}
        for s in sessions:
            pdf = session_positions[s.session_id]
            sub = pdf.filter(pl.col("product") == product).sort("timestamp")
            if sub.is_empty():
                pos_out[product][s.session_id] = {"x": [], "y": []}
                continue
            xs, ys = lttb(sub["timestamp"], sub["position"].cast(pl.Float64), target_points)
            pos_out[product][s.session_id] = {"x": xs.to_list(), "y": ys.to_list()}

    # ---- divergences: align per (product, ts) across all sessions, keep rows that differ ----
    divergences: list[dict] = []
    if len(sessions) >= 2:
        joined: pl.DataFrame | None = None
        for s in sessions:
            pdf = session_positions[s.session_id]
            if pdf.is_empty():
                continue
            renamed = pdf.select(["timestamp", "product", pl.col("position").alias(s.session_id)])
            joined = renamed if joined is None else joined.join(
                renamed, on=["timestamp", "product"], how="outer_coalesce"
            )
        if joined is not None and not joined.is_empty():
            cols = [s.session_id for s in sessions if s.session_id in joined.columns]
            if len(cols) >= 2:
                # rows where any two differ (ignoring nulls by forward-filling)
                filled = joined.sort(["product", "timestamp"]).with_columns([
                    pl.col(c).forward_fill().over("product") for c in cols
                ])
                first = cols[0]
                mask = pl.lit(False)
                for c in cols[1:]:
                    mask = mask | (pl.col(first) != pl.col(c))
                diff = filled.filter(mask).head(500)
                divergences = [
                    {
                        "ts": int(row["timestamp"]),
                        "product": row["product"],
                        **{c: (int(row[c]) if row[c] is not None else None) for c in cols},
                    }
                    for row in diff.to_dicts()
                ]

    return {
        "sids": [s.session_id for s in sessions],
        "pnl": pnl_out,
        "position": pos_out,
        "divergences": divergences,
    }
