from __future__ import annotations

import polars as pl

from app.modules.market_data.schemas import Filters


def apply(lf: pl.LazyFrame, f: Filters) -> pl.LazyFrame:
    """Compose lazy filter predicates. Unset fields become no-ops."""
    if f.products:
        lf = lf.filter(pl.col("product").cast(pl.Utf8).is_in(f.products))
    if f.days:
        lf = lf.filter(pl.col("day").is_in(f.days))
    if f.ts_range is not None:
        lo, hi = f.ts_range
        lf = lf.filter(pl.col("timestamp").is_between(lo, hi, closed="both"))
    if f.pnl_min is not None:
        lf = lf.filter(pl.col("profit_and_loss") >= f.pnl_min)
    if f.pnl_max is not None:
        lf = lf.filter(pl.col("profit_and_loss") <= f.pnl_max)
    return lf
