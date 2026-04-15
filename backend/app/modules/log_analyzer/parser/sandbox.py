"""Pass 3 — index sandbox/lambda log lines for the State Inspector.

Prosperity 4 (JSON format):
    section.raw = [{"timestamp": 0, "sandboxLog": "", "lambdaLog": "..."}, ...]

Older text format:
    section.text = raw lines, each either a JSON object or a plain print() line.

Both paths produce the same output frame:
    line_no | timestamp | level | product_tag | text
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

import polars as pl

_LEADING_TICK_RE = re.compile(r"^\s*\[?(?P<ts>-?\d{3,})\]?\b")
_LEVEL_RE = re.compile(r"\b(DEBUG|INFO|WARN|WARNING|ERROR|CRITICAL)\b", re.IGNORECASE)


@dataclass
class SandboxParseResult:
    frame: pl.DataFrame
    errors: list[dict]


def _extract_level(text: str) -> str | None:
    m = _LEVEL_RE.search(text)
    return m.group(1).upper() if m else None


def _extract_tick(text: str) -> int | None:
    m = _LEADING_TICK_RE.match(text)
    return int(m.group("ts")) if m else None


def _match_product(text: str, products: list[str]) -> str | None:
    for p in products:
        if p and p in text:
            return p
    return None


def _rows_from_json_array(
    entries: list[dict],
    products: list[str],
) -> tuple[list[dict], list[dict]]:
    """Parse the Prosperity 4 `logs` array."""
    rows: list[dict] = []
    errors: list[dict] = []
    for i, entry in enumerate(entries):
        ts = entry.get("timestamp")
        lambda_log = str(entry.get("lambdaLog") or entry.get("sandboxLog") or "").strip()
        if not lambda_log:
            continue
        # lambdaLog can itself contain multiple newline-separated print lines.
        for line in lambda_log.splitlines():
            line = line.strip()
            if not line:
                continue
            rows.append({
                "line_no": len(rows),
                "timestamp": ts,
                "level": _extract_level(line),
                "product_tag": _match_product(line, products),
                "text": line,
            })
    return rows, errors


def _rows_from_text(text: str, products: list[str]) -> tuple[list[dict], list[dict]]:
    """Parse the older plain-text sandbox section."""
    lines = text.splitlines()
    rows: list[dict] = []
    errors: list[dict] = []

    for i, raw in enumerate(lines):
        if not raw.strip():
            continue
        ts: int | None = None
        text_out = raw

        if raw.strip().startswith("{") and raw.strip().endswith("}"):
            try:
                obj = json.loads(raw.strip())
                ts = obj.get("timestamp")
                lambda_log = obj.get("lambdaLog") or obj.get("sandboxLog") or ""
                text_out = str(lambda_log).strip() or raw
            except json.JSONDecodeError as e:
                errors.append({"line": i, "reason": f"sandbox JSON: {e.msg}"})

        if ts is None:
            ts = _extract_tick(text_out)

        rows.append({
            "line_no": i,
            "timestamp": ts,
            "level": _extract_level(text_out),
            "product_tag": _match_product(text_out, products),
            "text": text_out,
        })

    return rows, errors


def parse_sandbox(
    text: str,
    *,
    known_products: list[str] | None = None,
    raw: object = None,
) -> SandboxParseResult:
    """Entry point — accepts either `.raw` (JSON list) or `.text` (plain text)."""
    products = known_products or []

    if isinstance(raw, list):
        rows, errors = _rows_from_json_array(raw, products)
    else:
        rows, errors = _rows_from_text(text, products)

    if not rows:
        frame = pl.DataFrame(schema={
            "line_no": pl.Int64, "timestamp": pl.Int64,
            "level": pl.Categorical, "product_tag": pl.Utf8, "text": pl.Utf8,
        })
    else:
        frame = pl.DataFrame(rows).with_columns(
            pl.col("line_no").cast(pl.Int64),
            pl.col("timestamp").cast(pl.Int64, strict=False),
            pl.col("level").cast(pl.Utf8).cast(pl.Categorical),
            pl.col("product_tag").cast(pl.Utf8),
            pl.col("text").cast(pl.Utf8),
        ).sort(["timestamp", "line_no"], nulls_last=True)

    return SandboxParseResult(frame=frame, errors=errors)
