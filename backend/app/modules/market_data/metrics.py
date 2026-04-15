"""On-the-fly metric computation for Module 1.

All functions take a Polars LazyFrame shaped like the *unified* view (i.e. what
`joiner.build_unified` emits) and return either a LazyFrame with added columns
or a dict-shaped payload ready for the API envelope.

Polars ≥ 1.0 API notes:
  - rolling_mean / rolling_std use `min_periods` (was `min_samples` pre-1.0)
  - Expr.replace(scalar, scalar) is gone; use pl.when().then().otherwise()
  - ewm_mean(span=...) still valid
"""
from __future__ import annotations

import polars as pl


# ---------- per-row metrics ----------
def microprice(lf: pl.LazyFrame) -> pl.LazyFrame:
    """ (ask_vol_1*bid_1 + bid_vol_1*ask_1) / (bid_vol_1 + ask_vol_1) """
    num = pl.col("ask_volume_1") * pl.col("bid_price_1") + pl.col("bid_volume_1") * pl.col("ask_price_1")
    den = pl.col("bid_volume_1") + pl.col("ask_volume_1")
    return lf.with_columns(
        pl.when(den > 0).then(num / den).otherwise(None).alias("microprice")
    )


def wobi(lf: pl.LazyFrame, levels: int = 3) -> pl.LazyFrame:
    """Weighted Order Book Imbalance across N levels."""
    levels = max(1, min(levels, 3))
    bid_sum = sum(
        (levels - i) * pl.col(f"bid_volume_{i + 1}").fill_null(0) for i in range(levels)
    )
    ask_sum = sum(
        (levels - i) * pl.col(f"ask_volume_{i + 1}").fill_null(0) for i in range(levels)
    )
    denom = bid_sum + ask_sum
    return lf.with_columns(
        pl.when(denom > 0).then((bid_sum - ask_sum) / denom).otherwise(None).alias("wobi")
    )


def ema(lf: pl.LazyFrame, *, window: int, column: str = "mid_price") -> pl.LazyFrame:
    return lf.with_columns(
        pl.col(column).ewm_mean(span=window).over(["day", "product"]).alias(f"ema_{window}")
    )


def sma(lf: pl.LazyFrame, *, window: int, column: str = "mid_price") -> pl.LazyFrame:
    return lf.with_columns(
        pl.col(column)
          .rolling_mean(window_size=window, min_periods=1)
          .over(["day", "product"])
          .alias(f"sma_{window}")
    )


def zscore(lf: pl.LazyFrame, *, window: int, on: str = "mid_price") -> pl.LazyFrame:
    mean = pl.col(on).rolling_mean(window_size=window, min_periods=1)
    std = pl.col(on).rolling_std(window_size=window, min_periods=2)
    return lf.with_columns(
        pl.when(std > 0)
          .then((pl.col(on) - mean) / std)
          .otherwise(0.0)
          .over(["day", "product"])
          .alias(f"zscore_{on}_{window}")
    )


# ---------- aggregated metrics ----------
def vwap(lf: pl.LazyFrame, *, bucket: str = "day") -> pl.LazyFrame:
    """Running VWAP per product, bucketed per day or per tick."""
    keys = ["day", "product"] if bucket == "day" else ["day", "product", "timestamp"]
    cum_pxq = (pl.col("vwap_tick").fill_null(0) * pl.col("trade_volume")).cum_sum().over(keys)
    cum_vol = pl.col("trade_volume").cum_sum().over(keys)
    return lf.with_columns(
        pl.when(cum_vol > 0).then(cum_pxq / cum_vol).otherwise(None).alias(f"vwap_{bucket}")
    )


def compute_all(
    lf: pl.LazyFrame,
    *,
    microprice_on: bool = False,
    wobi_levels: int | None = None,
    ema_window: int | None = None,
    sma_window: int | None = None,
    zscore_window: int | None = None,
    zscore_on: str = "mid_price",
    vwap_bucket: str | None = None,
) -> pl.LazyFrame:
    if microprice_on:
        lf = microprice(lf)
    if wobi_levels:
        lf = wobi(lf, levels=wobi_levels)
    if ema_window:
        lf = ema(lf, window=ema_window)
    if sma_window:
        lf = sma(lf, window=sma_window)
    if zscore_window:
        lf = zscore(lf, window=zscore_window, on=zscore_on)
    if vwap_bucket:
        lf = vwap(lf, bucket=vwap_bucket)
    return lf
