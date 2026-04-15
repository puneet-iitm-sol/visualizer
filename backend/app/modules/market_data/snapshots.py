"""Microstructure snapshot builder for the right-side inspector."""
from __future__ import annotations

from typing import Any

import polars as pl

from app.modules.market_data.metrics import compute_all


def _book_rows(row: dict) -> dict[str, list]:
    return {
        "bids": [[row[f"bid_price_{i}"], row[f"bid_volume_{i}"]] for i in (1, 2, 3)],
        "asks": [[row[f"ask_price_{i}"], row[f"ask_volume_{i}"]] for i in (1, 2, 3)],
    }


def snapshot(
    unified: pl.LazyFrame,
    trades: pl.LazyFrame | None,
    *,
    timestamp: int,
    product: str,
    day: int | None = None,
    context: int = 5,
) -> dict[str, Any]:
    lf = unified.filter(pl.col("product").cast(pl.Utf8) == product)
    if day is not None:
        lf = lf.filter(pl.col("day") == day)

    # Enrich with metrics so the panel has microprice + WOBI + rolling zscore.
    lf = compute_all(lf, microprice_on=True, wobi_levels=3, zscore_window=200)

    df = lf.filter(
        pl.col("timestamp").is_between(timestamp - context * 100, timestamp + context * 100)
    ).sort("timestamp").collect()

    if df.is_empty():
        return {"timestamp": timestamp, "product": product, "book": None, "trades_at_ts": [],
                "metrics": {}, "context": []}

    # Pick the row closest to the requested timestamp as the focal snapshot.
    focal = df.with_columns((pl.col("timestamp") - timestamp).abs().alias("__d__"))
    focal = focal.sort("__d__").head(1).drop("__d__").to_dicts()[0]

    trades_rows: list[dict] = []
    if trades is not None:
        trades_df = trades.filter(
            (pl.col("symbol").cast(pl.Utf8) == product) & (pl.col("timestamp") == focal["timestamp"])
        )
        if day is not None:
            trades_df = trades_df.filter(pl.col("day") == day)
        trades_rows = trades_df.collect().to_dicts()

    return {
        "timestamp": int(focal["timestamp"]),
        "product": product,
        "day": int(focal["day"]),
        "book": _book_rows(focal),
        "trades_at_ts": trades_rows,
        "metrics": {
            "microprice": focal.get("microprice"),
            "wobi": focal.get("wobi"),
            "zscore_mid_200": focal.get("zscore_mid_price_200"),
            "spread": focal.get("spread"),
            "mid_price": focal.get("mid_price"),
        },
        "context": [
            {
                "timestamp": int(r["timestamp"]),
                "mid_price": r["mid_price"],
                "spread": r["spread"],
                "trade_volume": r.get("trade_volume", 0),
                "microprice": r.get("microprice"),
                "wobi": r.get("wobi"),
            }
            for r in df.to_dicts()
        ],
    }
