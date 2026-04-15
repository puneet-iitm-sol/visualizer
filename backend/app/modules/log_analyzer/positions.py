"""Derive position / realized PnL time series from Trade History.

Trade History inside a submission log IS the algo's executed fills. We identify
*direction* by looking at buyer / seller:

    * buyer  in {"", "SUBMISSION", None}   → own BUY  (+qty)
    * seller in {"", "SUBMISSION", None}   → own SELL (-qty)
    * if both sides are "external"         → skipped (shouldn't occur in log)

Realized PnL uses a running weighted-average cost basis: sales against an open
long lock in (sell_px - avg_cost) * qty.
"""
from __future__ import annotations

import polars as pl

_OWN_MARKERS = {"", "SUBMISSION", "submission"}


def _own_side_expr() -> pl.Expr:
    is_buy = pl.col("buyer").fill_null("").is_in(list(_OWN_MARKERS))
    is_sell = pl.col("seller").fill_null("").is_in(list(_OWN_MARKERS))
    return (
        pl.when(is_buy & ~is_sell).then(pl.col("quantity"))
        .when(is_sell & ~is_buy).then(-pl.col("quantity"))
        .when(is_buy & is_sell).then(0)     # defensive: both blank → neutral
        .otherwise(0)
        .cast(pl.Int32)
    )


def build_positions(trades: pl.DataFrame | pl.LazyFrame) -> pl.DataFrame:
    """Return a tidy frame: (timestamp, product, position, realized_pnl)."""
    lf = trades.lazy() if isinstance(trades, pl.DataFrame) else trades

    if lf.collect_schema().len() == 0:
        return pl.DataFrame(schema={
            "timestamp": pl.Int64, "product": pl.Categorical,
            "position": pl.Int32, "realized_pnl": pl.Float64,
        })

    flagged = lf.with_columns(
        _own_side_expr().alias("signed_qty"),
        pl.col("symbol").cast(pl.Utf8).alias("product"),
    ).sort(["product", "timestamp"])

    # Running position via cumsum per product.
    with_pos = flagged.with_columns(
        pl.col("signed_qty").cum_sum().over("product").alias("position"),
    )

    # Realized PnL via a python-side walk per product — clearer than a
    # closed-form expression, and trade_history is almost always small (<10k rows).
    df = with_pos.collect()
    realized: list[float] = [0.0] * df.height

    by_product: dict[str, tuple[int, float, float]] = {}   # pos, avg_cost, cum_realized
    for i in range(df.height):
        p = df["product"][i]
        qty = int(df["signed_qty"][i])
        px = float(df["price"][i])
        pos, avg, cum = by_product.get(p, (0, 0.0, 0.0))

        if qty > 0:
            new_pos = pos + qty
            if pos >= 0:
                avg = (avg * pos + px * qty) / new_pos if new_pos else 0.0
            else:
                # covering a short
                close_qty = min(qty, -pos)
                cum += (avg - px) * close_qty
                remaining = qty - close_qty
                if remaining > 0:
                    avg = px
            pos = new_pos
        elif qty < 0:
            sell_qty = -qty
            new_pos = pos + qty
            if pos > 0:
                close_qty = min(sell_qty, pos)
                cum += (px - avg) * close_qty
                remaining = sell_qty - close_qty
                if remaining > 0:
                    avg = px   # flipping long → short
            else:
                avg = (avg * (-pos) + px * sell_qty) / (-new_pos) if new_pos else 0.0
            pos = new_pos

        by_product[p] = (pos, avg, cum)
        realized[i] = cum

    return df.with_columns(pl.Series("realized_pnl", realized, dtype=pl.Float64)).select([
        "timestamp", "product", "position", "realized_pnl",
    ])
