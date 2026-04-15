"""End-to-end Prosperity `.log` ingestion.

Usage
-----
    result = ingest_log("round1.log", path.read_bytes())
    session.activities      = result.activities.lazy()
    session.trade_history   = result.trade_history.lazy()
    session.sandbox         = result.sandbox.lazy()
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import polars as pl

from app.core.io import decode_text
from app.modules.log_analyzer.parser import (
    Section,
    SectionKind,
    parse_activities,
    parse_sandbox,
    parse_trade_history,
    split_sections,
)


@dataclass
class LogFileReport:
    name: str
    sections_found: list[str]
    sandbox_lines: int
    activities_rows: int
    trade_history_rows: int
    parse_errors: list[dict] = field(default_factory=list)


@dataclass
class LogIngestResult:
    activities: pl.DataFrame
    trade_history: pl.DataFrame
    sandbox: pl.DataFrame
    reports: list[LogFileReport]


def _pick(sections: list[Section], kind: SectionKind) -> Section | None:
    for s in sections:
        if s.kind is kind:
            return s
    return None


def ingest_log(name: str, data: bytes) -> LogIngestResult:
    return ingest_logs([(name, data)])


def ingest_logs(files: Iterable[tuple[str, bytes]]) -> LogIngestResult:
    activities_frames: list[pl.DataFrame] = []
    trades_frames: list[pl.DataFrame] = []
    sandbox_frames: list[pl.DataFrame] = []
    reports: list[LogFileReport] = []

    for name, data in files:
        text = decode_text(data)
        sections = split_sections(text)

        act_sec = _pick(sections, SectionKind.ACTIVITIES)
        trd_sec = _pick(sections, SectionKind.TRADE_HISTORY)
        sbx_sec = _pick(sections, SectionKind.SANDBOX)

        errs: list[dict] = []

        if act_sec is not None:
            out = parse_activities(act_sec.text)
            act_df = (
                out.frame.with_columns(pl.lit(name).alias("__source__"))
                if out.frame.height else pl.DataFrame()
            )
            errs.extend({"file": name, **e} for e in out.errors)
        else:
            act_df = pl.DataFrame()
            if sections and all(s.kind.value == "unknown" for s in sections):
                errs.append({"file": name, "reason": "no recognisable sections found — check log format"})

        if trd_sec is not None:
            out = parse_trade_history(trd_sec.text, raw=trd_sec.raw)
            trd_df = (
                out.frame.with_columns(pl.lit(name).alias("__source__"))
                if out.frame.height else pl.DataFrame()
            )
            errs.extend({"file": name, **e} for e in out.errors)
        else:
            trd_df = pl.DataFrame()

        # Known products for tag extraction — pull from both Activities (column
        # `product`) and Trade History (column `symbol`). Using both means a
        # sandbox line referencing a product only seen in trades still gets tagged.
        product_set: set[str] = set()
        if act_df.height and "product" in act_df.columns:
            product_set.update(
                act_df.select(pl.col("product").cast(pl.Utf8))
                      .to_series()
                      .drop_nulls()
                      .to_list()
            )
        if trd_df.height and "symbol" in trd_df.columns:
            product_set.update(
                trd_df.select(pl.col("symbol").cast(pl.Utf8))
                      .to_series()
                      .drop_nulls()
                      .to_list()
            )
        products = sorted(product_set)

        if sbx_sec is not None:
            sbx = parse_sandbox(sbx_sec.text, known_products=products, raw=sbx_sec.raw)
            sbx_df = (
                sbx.frame.with_columns(pl.lit(name).alias("__source__"))
                if sbx.frame.height else pl.DataFrame()
            )
            errs.extend({"file": name, **e} for e in sbx.errors)
        else:
            sbx_df = pl.DataFrame()

        activities_frames.append(act_df)
        trades_frames.append(trd_df)
        sandbox_frames.append(sbx_df)

        reports.append(
            LogFileReport(
                name=name,
                sections_found=[s.kind.value for s in sections if s.kind is not SectionKind.UNKNOWN],
                sandbox_lines=sbx_df.height,
                activities_rows=act_df.height,
                trade_history_rows=trd_df.height,
                parse_errors=errs,
            )
        )

    activities = pl.concat(
        [f for f in activities_frames if f.height], how="vertical_relaxed"
    ) if any(f.height for f in activities_frames) else pl.DataFrame()

    trade_history = pl.concat(
        [f for f in trades_frames if f.height], how="vertical_relaxed"
    ) if any(f.height for f in trades_frames) else pl.DataFrame()

    sandbox = pl.concat(
        [f for f in sandbox_frames if f.height], how="vertical_relaxed"
    ) if any(f.height for f in sandbox_frames) else pl.DataFrame()

    return LogIngestResult(
        activities=activities,
        trade_history=trade_history,
        sandbox=sandbox,
        reports=reports,
    )


def ingest_log_paths(paths: Iterable[str | Path]) -> LogIngestResult:
    return ingest_logs([(Path(p).name, Path(p).read_bytes()) for p in paths])
