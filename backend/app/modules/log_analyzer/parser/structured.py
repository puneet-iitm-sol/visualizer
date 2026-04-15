"""Pass 2 — turn the Activities and Trade-History section bodies into typed
Polars DataFrames.

Activities section = same layout as prices_round_*.csv but we are LENIENT:
only timestamp, product, mid_price are strictly required. All bid/ask levels
and profit_and_loss are padded with nulls if absent so partial order-book logs
(Prosperity 4 tutorial day, restricted products, etc.) still parse cleanly.

Trade History = either a JSON array OR semicolon-CSV.  Prosperity has shipped
both forms across rounds; we try JSON first and fall back to CSV.
"""
from __future__ import annotations

import io
import json
from dataclasses import dataclass

import polars as pl

from app.modules.market_data.parser import (
    PRICES_COLUMNS,
    TRADES_COLUMNS,
    _coerce_trades,
    _normalize_columns,
    _PRICES_ALIASES,
)


@dataclass
class ParseOutcome:
    frame: pl.DataFrame
    errors: list[dict]


# Columns we MUST have to call the activities parse meaningful.
_REQUIRED_ACTIVITY_COLS = {"timestamp", "product", "mid_price"}

# Optional columns — padded with null if absent.
_OPTIONAL_FLOAT_COLS = [
    c for c in PRICES_COLUMNS
    if c.startswith(("bid_price", "ask_price")) or c in ("profit_and_loss",)
]
_OPTIONAL_INT_COLS = [
    c for c in PRICES_COLUMNS if c.startswith(("bid_volume", "ask_volume"))
]


def _pad_missing(df: pl.DataFrame) -> pl.DataFrame:
    """Add any PRICES_COLUMNS that are absent, filled with null."""
    for col in PRICES_COLUMNS:
        if col not in df.columns:
            if col in _OPTIONAL_FLOAT_COLS:
                df = df.with_columns(pl.lit(None, dtype=pl.Float64).alias(col))
            elif col in _OPTIONAL_INT_COLS:
                df = df.with_columns(pl.lit(None, dtype=pl.Int32).alias(col))
    return df


def parse_activities(text: str) -> ParseOutcome:
    """Parse the Activities section body (CSV with `;` separators)."""
    body = text.strip()
    if not body:
        return ParseOutcome(pl.DataFrame(), [])

    errors: list[dict] = []

    try:
        raw = pl.read_csv(
            io.StringIO(body),
            separator=";",
            infer_schema_length=5000,
            ignore_errors=True,
            null_values=["", "nan", "NaN"],
        )
    except Exception as e:
        return ParseOutcome(pl.DataFrame(), [{"reason": f"read_csv failed: {e}"}])

    if raw.is_empty():
        return ParseOutcome(pl.DataFrame(), [{"reason": "activities section parsed to 0 rows"}])

    # Normalise column names (lowercase, apply aliases).
    raw = _normalize_columns(raw, _PRICES_ALIASES)

    # Inject `day` from col if present, else default 0.
    if "day" not in raw.columns:
        raw = raw.with_columns(pl.lit(0, dtype=pl.Int8).alias("day"))

    # Check minimum required columns.
    missing_required = _REQUIRED_ACTIVITY_COLS - set(raw.columns)
    if missing_required:
        return ParseOutcome(
            pl.DataFrame(),
            [{"reason": f"activities missing required columns: {sorted(missing_required)}; "
                        f"file has: {raw.columns}"}],
        )

    # Pad any missing optional columns with null so downstream can rely on full schema.
    raw = _pad_missing(raw)

    # Select + cast into canonical types.
    try:
        df = raw.select(PRICES_COLUMNS).with_columns(
            pl.col("day").cast(pl.Int8, strict=False),
            pl.col("timestamp").cast(pl.Int64, strict=False),
            pl.col("product").cast(pl.Utf8).cast(pl.Categorical),
            *[pl.col(c).cast(pl.Float64, strict=False)
              for c in PRICES_COLUMNS if c.startswith(("bid_price", "ask_price", "mid_", "profit_"))],
            *[pl.col(c).cast(pl.Int32, strict=False)
              for c in PRICES_COLUMNS if c.startswith(("bid_volume", "ask_volume"))],
        )
    except Exception as e:
        errors.append({"reason": f"type coercion failed: {e}"})
        return ParseOutcome(pl.DataFrame(), errors)

    return ParseOutcome(df, errors)


# ---------- Trade History ----------
def _trade_history_from_json(body: str) -> list[dict]:
    trimmed = body.strip().rstrip(",")
    if not trimmed.startswith("["):
        return []
    return json.loads(trimmed)


def _trade_history_from_csv(body: str) -> pl.DataFrame:
    return pl.read_csv(
        io.StringIO(body),
        separator=";",
        infer_schema_length=5000,
        ignore_errors=True,
        null_values=["", "nan"],
    )


def parse_trade_history(text: str, *, raw: object = None) -> ParseOutcome:
    """Parse trade history from either a pre-parsed list (JSON format) or raw text."""
    # Prosperity 4: raw is already a Python list of dicts.
    if isinstance(raw, list):
        if not raw:
            return ParseOutcome(pl.DataFrame(), [])
        try:
            df = pl.from_dicts(raw)
            df = _coerce_trades(df, day_hint=0)
            return ParseOutcome(df, [])
        except Exception as e:
            return ParseOutcome(pl.DataFrame(), [{"reason": f"tradeHistory coercion: {e}"}])

    body = text.strip()
    if not body:
        return ParseOutcome(pl.DataFrame(), [])

    errors: list[dict] = []
    df: pl.DataFrame

    try:
        records = _trade_history_from_json(body)
        if records:
            df = pl.from_dicts(records)
        else:
            df = _trade_history_from_csv(body)
    except json.JSONDecodeError as e:
        errors.append({"reason": f"trade-history JSON: {e.msg} (line {e.lineno})"})
        try:
            df = _trade_history_from_csv(body)
        except Exception as e2:
            return ParseOutcome(pl.DataFrame(), errors + [{"reason": f"CSV fallback failed: {e2}"}])

    if df.is_empty():
        return ParseOutcome(pl.DataFrame(), errors + [{"reason": "trade history is empty"}])

    try:
        df = _coerce_trades(df, day_hint=0)
    except Exception as e:
        errors.append({"reason": f"trade coercion failed: {e}; columns: {df.columns}"})
        return ParseOutcome(pl.DataFrame(), errors)

    return ParseOutcome(df, errors)
