"""Chart-series builder for Module 1.

Turns a filtered `unified` LazyFrame + a list of requested series into the flat
`{"x": [...], "series": {...}}` payload the frontend consumes, applying
server-side downsampling so the wire format stays small.
"""
from __future__ import annotations

from typing import Any

import polars as pl

from app.core.downsample import bucket_mean, lttb
from app.modules.market_data.metrics import compute_all
from app.modules.market_data.schemas import Downsample, SeriesKind


# Which unified-frame column backs each simple series?
_SIMPLE: dict[str, str] = {
    "mid": "mid_price",
    "bid_1": "bid_price_1",
    "ask_1": "ask_price_1",
    "spread": "spread",
    "volume": "trade_volume",
    "pnl": "cum_pnl",
}


def _metric_flags(series: list[SeriesKind]) -> dict[str, Any]:
    """Enable only the metrics the request actually needs."""
    flags: dict[str, Any] = {}
    if "microprice" in series:
        flags["microprice_on"] = True
    if "wobi" in series:
        flags["wobi_levels"] = 3
    if "ema" in series:
        flags["ema_window"] = 50
    if "sma" in series:
        flags["sma_window"] = 200
    if "zscore" in series:
        flags["zscore_window"] = 200
    if "vwap" in series:
        flags["vwap_bucket"] = "day"
    return flags


def _metric_col(kind: str) -> str | None:
    return {
        "microprice": "microprice",
        "wobi": "wobi",
        "ema": "ema_50",
        "sma": "sma_200",
        "zscore": "zscore_mid_price_200",
        "vwap": "vwap_day",
    }.get(kind)


def _downsample_series(x: pl.Series, y: pl.Series, ds: Downsample) -> tuple[list, list]:
    if ds.method == "lttb":
        dx, dy = lttb(x, y, ds.target_points)
        return dx.to_list(), dy.to_list()
    # bucket
    df = pl.DataFrame({"x": x, "y": y})
    out = bucket_mean(df, x_col="x", y_cols=["y"], target=ds.target_points)
    return out["x"].to_list(), out["y"].to_list()


def build_series(
    unified: pl.LazyFrame,
    trades: pl.LazyFrame | None,
    *,
    series: list[SeriesKind],
    downsample: Downsample,
) -> dict[str, Any]:
    # Attach any requested metric columns lazily.
    lf = compute_all(unified, **_metric_flags(series))
    df = lf.sort(["product", "day", "timestamp"]).collect()

    if df.is_empty():
        return {"x": [], "series": {}, "downsampled": False, "original_points": 0}

    # Group by product so each product gets its own Y-array per series.
    per_product = dict(df.group_by("product", maintain_order=True).__iter__())
    original_points = df.height

    out_series: dict[str, dict[str, Any]] = {k: {} for k in series}
    x_union: list[int] = []

    for prod_key, sub in per_product.items():
        product = str(prod_key[0] if isinstance(prod_key, tuple) else prod_key)
        sub = sub.sort("timestamp")
        x_ts = sub["timestamp"]

        for kind in series:
            if kind in _SIMPLE:
                col = _SIMPLE[kind]
                if col not in sub.columns:
                    continue
                if kind == "pnl":
                    xs, ys = _downsample_series(x_ts, sub[col].cast(pl.Float64), downsample)
                    out_series["pnl"][product] = ys
                    out_series["pnl"].setdefault("__x__", xs)
                else:
                    xs, ys = _downsample_series(x_ts, sub[col].cast(pl.Float64), downsample)
                    out_series[kind][product] = ys
                    out_series[kind].setdefault("__x__", xs)

            elif kind == "depth":
                out_series["depth"][product] = {
                    "bid": [
                        [sub["bid_volume_1"][i] or 0, sub["bid_volume_2"][i] or 0, sub["bid_volume_3"][i] or 0]
                        for i in range(sub.height)
                    ],
                    "ask": [
                        [sub["ask_volume_1"][i] or 0, sub["ask_volume_2"][i] or 0, sub["ask_volume_3"][i] or 0]
                        for i in range(sub.height)
                    ],
                    "__x__": x_ts.to_list(),
                }

            elif kind == "trades" and trades is not None:
                tdf = (
                    trades.filter(pl.col("symbol").cast(pl.Utf8) == product)
                    .sort("timestamp")
                    .collect()
                )
                out_series["trades"][product] = [
                    {
                        "ts": int(row["timestamp"]),
                        "px": float(row["price"]),
                        "qty": int(row["quantity"]),
                        "buyer": row.get("buyer"),
                        "seller": row.get("seller"),
                    }
                    for row in tdf.to_dicts()
                ]

            else:
                col = _metric_col(kind)
                if col and col in sub.columns:
                    xs, ys = _downsample_series(x_ts, sub[col].cast(pl.Float64), downsample)
                    out_series[kind][product] = ys
                    out_series[kind].setdefault("__x__", xs)

        if len(x_ts) > len(x_union):
            x_union = x_ts.to_list()

    # Aggregate PnL total across products when pnl was requested.
    if "pnl" in series and any(k != "__x__" for k in out_series["pnl"]):
        prod_keys = [k for k in out_series["pnl"] if k != "__x__"]
        if prod_keys:
            mat = [out_series["pnl"][k] for k in prod_keys]
            length = min(len(v) for v in mat)
            out_series["pnl"]["__total__"] = [
                sum(mat[p][i] for p in range(len(prod_keys))) for i in range(length)
            ]

    return {
        "x": x_union,
        "series": out_series,
        "downsampled": any(
            s != "__x__" and isinstance(out_series[k].get(s), list)
            and len(out_series[k].get(s, [])) < original_points
            for k in out_series for s in out_series[k]
        ),
        "original_points": original_points,
    }
