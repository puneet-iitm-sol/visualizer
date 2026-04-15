"""Module 1 — Prosperity CSV ingestion.

Handles the official `prices_round_X_day_Y.csv` and `trades_round_X_day_Y*.csv`
drops. Files use semicolons as separators; columns are stable but we still map
defensively because Prosperity has changed spellings between rounds (e.g.
`profit_and_loss` vs. `pnl`, `symbol` vs. `product`).

Returns Polars LazyFrames so downstream filter/aggregate plans stay lazy.
"""
from __future__ import annotations

import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import polars as pl

from app.core.errors import ParseError
from app.core.io import classify_csv, decode_text, sniff_separator

# -------- canonical schemas --------
PRICES_COLUMNS: list[str] = [
    "day", "timestamp", "product",
    "bid_price_1", "bid_volume_1",
    "bid_price_2", "bid_volume_2",
    "bid_price_3", "bid_volume_3",
    "ask_price_1", "ask_volume_1",
    "ask_price_2", "ask_volume_2",
    "ask_price_3", "ask_volume_3",
    "mid_price", "profit_and_loss",
]

TRADES_COLUMNS: list[str] = [
    "timestamp", "buyer", "seller", "symbol", "currency", "price", "quantity",
]

# Alternate spellings we have observed across Prosperity seasons.
_PRICES_ALIASES: dict[str, str] = {
    "pnl": "profit_and_loss",
    "profit_loss": "profit_and_loss",
    "midprice": "mid_price",
    "mid": "mid_price",
    "symbol": "product",
}

_TRADES_ALIASES: dict[str, str] = {
    "product": "symbol",
    "size": "quantity",
    "qty": "quantity",
    "px": "price",
}


@dataclass
class FileReport:
    name: str
    kind: str                      # "prices" | "trades"
    round: int | None
    day: int | None
    rows: int
    columns: list[str]
    errors: list[str] = field(default_factory=list)


@dataclass
class IngestResult:
    prices: pl.LazyFrame | None
    trades: pl.LazyFrame | None
    reports: list[FileReport]
    products: list[str]
    days: list[int]
    timestamp_range: tuple[int, int] | None


# -------- helpers --------
def _normalize_columns(df: pl.DataFrame, aliases: dict[str, str]) -> pl.DataFrame:
    rename = {}
    for col in df.columns:
        key = col.strip().lower()
        if key in aliases:
            rename[col] = aliases[key]
        elif col != key:
            rename[col] = key
    return df.rename(rename) if rename else df


def _coerce_prices(df: pl.DataFrame, *, day_hint: int | None) -> pl.DataFrame:
    df = _normalize_columns(df, _PRICES_ALIASES)
    if "day" not in df.columns:
        if day_hint is None:
            raise ParseError("prices file is missing `day` column and filename has no day hint")
        df = df.with_columns(pl.lit(day_hint).alias("day"))

    missing = [c for c in PRICES_COLUMNS if c not in df.columns]
    if missing:
        raise ParseError(f"prices file missing required columns: {missing}")

    return df.select(PRICES_COLUMNS).with_columns(
        pl.col("day").cast(pl.Int8, strict=False),
        pl.col("timestamp").cast(pl.Int64, strict=False),
        pl.col("product").cast(pl.Utf8).cast(pl.Categorical),
        *[pl.col(c).cast(pl.Float64, strict=False)
          for c in PRICES_COLUMNS if c.startswith(("bid_price", "ask_price", "mid_", "profit_"))],
        *[pl.col(c).cast(pl.Int32, strict=False)
          for c in PRICES_COLUMNS if c.startswith(("bid_volume", "ask_volume"))],
    )


def _coerce_trades(df: pl.DataFrame, *, day_hint: int | None) -> pl.DataFrame:
    df = _normalize_columns(df, _TRADES_ALIASES)

    if "day" not in df.columns:
        df = df.with_columns(pl.lit(day_hint if day_hint is not None else 0).alias("day"))

    # Trades files have only ever shipped with the canonical 7 columns; guard anyway.
    missing = [c for c in TRADES_COLUMNS if c not in df.columns]
    if missing:
        raise ParseError(f"trades file missing required columns: {missing}")

    return df.select(["day", *TRADES_COLUMNS]).with_columns(
        pl.col("day").cast(pl.Int8, strict=False),
        pl.col("timestamp").cast(pl.Int64, strict=False),
        pl.col("buyer").cast(pl.Utf8),
        pl.col("seller").cast(pl.Utf8),
        pl.col("symbol").cast(pl.Utf8).cast(pl.Categorical),
        pl.col("currency").cast(pl.Utf8).cast(pl.Categorical),
        pl.col("price").cast(pl.Float64, strict=False),
        pl.col("quantity").cast(pl.Int32, strict=False),
    )


def _read_csv_bytes(data: bytes) -> pl.DataFrame:
    text = decode_text(data)
    sep = sniff_separator(text[:4096])
    return pl.read_csv(
        io.StringIO(text),
        separator=sep,
        infer_schema_length=2000,
        try_parse_dates=False,
        ignore_errors=False,
    )


# -------- public entry points --------
_PRICES_HINT_COLS = {"bid_price_1", "ask_price_1", "mid_price"}
_TRADES_HINT_COLS = {"buyer", "seller", "symbol", "quantity"}


def _detect_kind(df: pl.DataFrame) -> str | None:
    """Fallback: infer prices vs trades from column set when filename is ambiguous."""
    cols = {c.lower() for c in df.columns}
    if _PRICES_HINT_COLS <= cols:
        return "prices"
    if _TRADES_HINT_COLS <= cols:
        return "trades"
    return None


def parse_file(name: str, data: bytes) -> tuple[str, pl.DataFrame, FileReport]:
    kind, rnd, day = classify_csv(name)

    try:
        raw = _read_csv_bytes(data)
    except Exception as e:
        raise ParseError(f"failed to read `{name}` as CSV: {e}", details={"name": name})

    # If filename didn't match, try to detect from column names.
    if kind is None:
        kind = _detect_kind(raw)
        if kind is None:
            raise ParseError(
                f"cannot classify `{name}` — name should match prices_round_*_day_* or "
                f"trades_round_*_day_*, or file must contain recognisable columns",
                details={"name": name, "columns": raw.columns},
            )

    try:
        df = _coerce_prices(raw, day_hint=day) if kind == "prices" else _coerce_trades(raw, day_hint=day)
    except ParseError:
        raise
    except Exception as e:
        raise ParseError(f"schema coercion failed for `{name}`: {e}", details={"name": name})

    return kind, df, FileReport(
        name=name, kind=kind, round=rnd, day=day, rows=df.height, columns=df.columns,
    )


def ingest(files: Iterable[tuple[str, bytes]]) -> IngestResult:
    """Parse every uploaded file and concatenate into lazy prices/trades frames."""
    price_frames: list[pl.DataFrame] = []
    trade_frames: list[pl.DataFrame] = []
    reports: list[FileReport] = []

    for name, data in files:
        try:
            kind, df, rep = parse_file(name, data)
        except ParseError as e:
            reports.append(FileReport(
                name=name, kind="unknown", round=None, day=None, rows=0,
                columns=[], errors=[e.message],
            ))
            continue
        reports.append(rep)
        (price_frames if kind == "prices" else trade_frames).append(df)

    if not price_frames and not trade_frames:
        errors = [e for r in reports for e in r.errors]
        raise ParseError(
            "no files could be parsed",
            details={"per_file_errors": errors},
        )

    prices_lf = pl.concat(price_frames, how="vertical_relaxed").lazy() if price_frames else None
    trades_lf = pl.concat(trade_frames, how="vertical_relaxed").lazy() if trade_frames else None

    # Metadata — compute once for the session.
    products: list[str] = []
    days: list[int] = []
    ts_range: tuple[int, int] | None = None

    if prices_lf is not None:
        summary = prices_lf.select([
            pl.col("timestamp").min().alias("ts_min"),
            pl.col("timestamp").max().alias("ts_max"),
        ]).collect()
        ts_range = (int(summary[0, "ts_min"]), int(summary[0, "ts_max"]))
        products = sorted(
            prices_lf.select(pl.col("product").cast(pl.Utf8))
                      .unique()
                      .collect()
                      .to_series()
                      .to_list()
        )
        days = sorted(
            prices_lf.select(pl.col("day").cast(pl.Int64))
                      .unique()
                      .collect()
                      .to_series()
                      .to_list()
        )

    return IngestResult(
        prices=prices_lf,
        trades=trades_lf,
        reports=reports,
        products=products,
        days=days,
        timestamp_range=ts_range,
    )


def ingest_paths(paths: Iterable[str | Path]) -> IngestResult:
    loaded = [(Path(p).name, Path(p).read_bytes()) for p in paths]
    return ingest(loaded)
