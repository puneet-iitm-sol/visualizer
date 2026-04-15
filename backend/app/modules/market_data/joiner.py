"""Unified view: prices ⟕ per-tick aggregated trades.

We keep the trades frame separately (one row per fill) because downstream charts
need both granularities. The *unified* view attaches per-tick summary stats so
a single filter+select can serve the main dashboard without re-aggregating.
"""
from __future__ import annotations

import polars as pl


def aggregate_trades(trades: pl.LazyFrame) -> pl.LazyFrame:
    """Collapse raw trades to one row per (day, timestamp, product)."""
    return (
        trades.rename({"symbol": "product"})
        .group_by(["day", "timestamp", "product"], maintain_order=True)
        .agg([
            pl.len().cast(pl.Int32).alias("trade_count"),
            pl.col("quantity").sum().cast(pl.Int32).alias("trade_volume"),
            ((pl.col("price") * pl.col("quantity")).sum()
             / pl.col("quantity").sum()).alias("vwap_tick"),
            pl.col("price").min().alias("trade_min"),
            pl.col("price").max().alias("trade_max"),
        ])
    )


def build_unified(prices: pl.LazyFrame, trades: pl.LazyFrame | None) -> pl.LazyFrame:
    """Left-join prices with per-tick trade aggregates.

    Derives three extra columns used by most dashboards:
      * spread            = ask_price_1 - bid_price_1
      * cum_pnl           = cumulative profit_and_loss per (day, product)
      * trade_volume      = 0 when no fills at that tick (null-coalesced)
    """
    unified = prices.with_columns(
        (pl.col("ask_price_1") - pl.col("bid_price_1")).alias("spread"),
        pl.col("profit_and_loss")
          .cum_sum()
          .over(["day", "product"])
          .alias("cum_pnl"),
    )

    if trades is None:
        return unified.with_columns(
            pl.lit(0, dtype=pl.Int32).alias("trade_count"),
            pl.lit(0, dtype=pl.Int32).alias("trade_volume"),
            pl.lit(None, dtype=pl.Float64).alias("vwap_tick"),
            pl.lit(None, dtype=pl.Float64).alias("trade_min"),
            pl.lit(None, dtype=pl.Float64).alias("trade_max"),
        )

    agg = aggregate_trades(trades)
    return (
        unified.join(agg, on=["day", "timestamp", "product"], how="left")
        .with_columns(
            pl.col("trade_count").fill_null(0),
            pl.col("trade_volume").fill_null(0),
        )
    )
