"""Smoke tests exercising both parsing engines against synthetic Prosperity-
style fixtures. Run with:

    cd backend
    python -m pytest tests/test_parsers.py -q

Or just execute this file directly — it has a `__main__` fallback so the same
checks work without pytest installed.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make `app.*` importable when run as a script.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import polars as pl

from app.modules.log_analyzer.ingest import ingest_logs
from app.modules.market_data.joiner import build_unified
from app.modules.market_data.parser import ingest


# ------------------------------------------------------------------
# Module 1 — Prosperity prices + trades CSV
# ------------------------------------------------------------------
PRICES_CSV = (
    "day;timestamp;product;"
    "bid_price_1;bid_volume_1;bid_price_2;bid_volume_2;bid_price_3;bid_volume_3;"
    "ask_price_1;ask_volume_1;ask_price_2;ask_volume_2;ask_price_3;ask_volume_3;"
    "mid_price;profit_and_loss\n"
    "0;0;KELP;2028;29;2027;15;2026;10;2031;25;2032;18;2033;11;2029.5;0\n"
    "0;100;KELP;2029;30;2028;12;2027;9;2031;22;2032;17;2033;10;2030.0;5\n"
    "0;0;RAINFOREST_RESIN;9998;50;9997;22;9996;10;10002;40;10003;20;10004;8;10000.0;0\n"
    "0;100;RAINFOREST_RESIN;9999;45;9998;25;9997;11;10002;38;10003;21;10004;9;10000.5;3\n"
)

TRADES_CSV = (
    "timestamp;buyer;seller;symbol;currency;price;quantity\n"
    "0;SUBMISSION;Olivia;KELP;SEASHELLS;2031;5\n"
    "100;SUBMISSION;Paulina;KELP;SEASHELLS;2030;3\n"
    "100;Ethan;SUBMISSION;RAINFOREST_RESIN;SEASHELLS;10001;4\n"
)


def test_market_ingest() -> None:
    result = ingest([
        ("prices_round_1_day_0.csv", PRICES_CSV.encode("utf-8")),
        ("trades_round_1_day_0_nn.csv", TRADES_CSV.encode("utf-8")),
    ])

    assert result.prices is not None, "prices LazyFrame should exist"
    assert result.trades is not None, "trades LazyFrame should exist"
    assert result.timestamp_range == (0, 100)
    assert set(result.products) == {"KELP", "RAINFOREST_RESIN"}
    assert result.days == [0]

    unified = build_unified(result.prices, result.trades).collect()

    assert unified.height == 4
    # spread derived correctly
    kelp_t0 = unified.filter((pl.col("product") == "KELP") & (pl.col("timestamp") == 0))
    assert kelp_t0["spread"][0] == 3.0  # 2031 - 2028
    # trade aggregation attached
    assert kelp_t0["trade_count"][0] == 1
    assert kelp_t0["trade_volume"][0] == 5
    assert kelp_t0["vwap_tick"][0] == 2031.0

    # cum_pnl should accumulate per product
    resin = unified.filter(pl.col("product") == "RAINFOREST_RESIN").sort("timestamp")
    assert resin["cum_pnl"].to_list() == [0.0, 3.0]

    print("[ok] Module 1 parse + join — rows =", unified.height)


# ------------------------------------------------------------------
# Module 2 — submission log file
# ------------------------------------------------------------------
LOG_FILE = """\
Sandbox logs:
{"timestamp":0,"sandboxLog":"","lambdaLog":"WOBI=0.12  considering KELP buy"}
{"timestamp":100,"sandboxLog":"","lambdaLog":"INFO fired order KELP@2031 qty=5"}
[200] raw print line, no json wrapper — RAINFOREST_RESIN fill

Activities log:
day;timestamp;product;bid_price_1;bid_volume_1;bid_price_2;bid_volume_2;bid_price_3;bid_volume_3;ask_price_1;ask_volume_1;ask_price_2;ask_volume_2;ask_price_3;ask_volume_3;mid_price;profit_and_loss
0;0;KELP;2028;29;2027;15;2026;10;2031;25;2032;18;2033;11;2029.5;0
0;100;KELP;2029;30;2028;12;2027;9;2031;22;2032;17;2033;10;2030.0;7

Trade History:
[
  {"timestamp": 100, "buyer": "SUBMISSION", "seller": "Paulina", "symbol": "KELP", "currency": "SEASHELLS", "price": 2031.0, "quantity": 5},
  {"timestamp": 200, "buyer": "Ethan", "seller": "SUBMISSION", "symbol": "RAINFOREST_RESIN", "currency": "SEASHELLS", "price": 10001.0, "quantity": 4}
]
"""


def test_log_ingest() -> None:
    result = ingest_logs([("round1.log", LOG_FILE.encode("utf-8"))])

    rep = result.reports[0]
    assert set(rep.sections_found) == {"sandbox", "activities", "trade_history"}, rep.sections_found
    assert rep.activities_rows == 2
    assert rep.trade_history_rows == 2
    assert rep.sandbox_lines == 3

    # Activities typed & sortable
    assert "mid_price" in result.activities.columns
    kelp = result.activities.filter(pl.col("product").cast(pl.Utf8) == "KELP").sort("timestamp")
    assert kelp["mid_price"].to_list() == [2029.5, 2030.0]

    # Trade History structured
    assert result.trade_history.height == 2
    assert result.trade_history["symbol"].cast(pl.Utf8).to_list() == ["KELP", "RAINFOREST_RESIN"]

    # Sandbox: timestamps extracted from both JSON and bracket-prefix forms.
    tss = result.sandbox["timestamp"].to_list()
    assert tss == [0, 100, 200]
    tags = result.sandbox["product_tag"].to_list()
    assert "KELP" in tags and "RAINFOREST_RESIN" in tags

    print("[ok] Module 2 parse — activities:", result.activities.height,
          "trades:", result.trade_history.height,
          "sandbox:", result.sandbox.height)


if __name__ == "__main__":
    test_market_ingest()
    test_log_ingest()
    print("\nall parser smoke tests passed.")
