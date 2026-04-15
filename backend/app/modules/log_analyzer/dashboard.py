"""Strategy dashboard series: algo PnL, position, executions per product."""
from __future__ import annotations

from typing import Any

import polars as pl

from app.core.downsample import lttb
from app.modules.log_analyzer.schemas import LogFilters


def _apply(lf: pl.LazyFrame, f: LogFilters, *, ts_col: str = "timestamp", product_col: str = "product") -> pl.LazyFrame:
    if f.products:
        lf = lf.filter(pl.col(product_col).cast(pl.Utf8).is_in(f.products))
    if f.ts_range is not None:
        lo, hi = f.ts_range
        lf = lf.filter(pl.col(ts_col).is_between(lo, hi, closed="both"))
    return lf


def _dsample(x: pl.Series, y: pl.Series, target: int) -> tuple[list, list]:
    dx, dy = lttb(x, y, target)
    return dx.to_list(), dy.to_list()


def build_dashboard(
    activities: pl.LazyFrame | None,
    positions: pl.LazyFrame | None,
    trades: pl.LazyFrame | None,
    *,
    filters: LogFilters,
    target_points: int,
) -> dict[str, Any]:
    pnl: dict[str, Any] = {}
    pos: dict[str, Any] = {}
    execs: dict[str, list[dict]] = {}
    x_union: list[int] = []

    if activities is not None:
        df = _apply(activities, filters).sort(["product", "timestamp"]).collect()
        if not df.is_empty():
            df = df.with_columns(
                pl.col("profit_and_loss").cum_sum().over("product").alias("__cum__")
            )
            for pkey, sub in df.group_by("product", maintain_order=True):
                product = str(pkey[0] if isinstance(pkey, tuple) else pkey)
                sub = sub.sort("timestamp")
                xs, ys = _dsample(sub["timestamp"], sub["__cum__"].cast(pl.Float64), target_points)
                pnl[product] = ys
                pnl.setdefault("__x__", xs)
                if len(xs) > len(x_union):
                    x_union = xs

            # Aggregate total PnL across products — align on each product's own x.
            keys = [k for k in pnl if k != "__x__"]
            if keys:
                length = min(len(pnl[k]) for k in keys)
                pnl["__total__"] = [sum(pnl[k][i] for k in keys) for i in range(length)]

    if positions is not None:
        pdf = _apply(positions, filters).sort(["product", "timestamp"]).collect()
        if not pdf.is_empty():
            for pkey, sub in pdf.group_by("product", maintain_order=True):
                product = str(pkey[0] if isinstance(pkey, tuple) else pkey)
                sub = sub.sort("timestamp")
                xs, ys = _dsample(sub["timestamp"], sub["position"].cast(pl.Float64), target_points)
                pos[product] = {"x": xs, "y": ys}

    if trades is not None:
        tdf = _apply(trades, filters, product_col="symbol").sort("timestamp").collect()
        for pkey, sub in tdf.group_by("symbol", maintain_order=True):
            product = str(pkey[0] if isinstance(pkey, tuple) else pkey)
            execs[product] = [
                {
                    "ts": int(row["timestamp"]),
                    "px": float(row["price"]),
                    "qty": int(row["quantity"]),
                    "buyer": row.get("buyer"),
                    "seller": row.get("seller"),
                }
                for row in sub.to_dicts()
            ]

    return {"x": x_union, "algo_pnl": pnl, "position": pos, "executions": execs}
