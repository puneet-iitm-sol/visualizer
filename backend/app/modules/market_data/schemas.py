from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

SeriesKind = Literal[
    "mid", "bid_1", "ask_1", "spread", "volume", "pnl", "depth", "trades",
    "microprice", "wobi", "ema", "sma", "zscore", "vwap",
]


class Filters(BaseModel):
    products: list[str] | None = None
    days: list[int] | None = None
    ts_range: tuple[int, int] | None = None
    pnl_min: float | None = None
    pnl_max: float | None = None


class Downsample(BaseModel):
    target_points: int = Field(default=8000, ge=100, le=200_000)
    method: Literal["lttb", "bucket"] = "lttb"


class QueryRequest(BaseModel):
    filters: Filters = Filters()
    series: list[SeriesKind] = ["mid", "bid_1", "ask_1", "spread", "volume", "pnl"]
    downsample: Downsample = Downsample()


class MetricOptions(BaseModel):
    microprice: bool = False
    wobi: dict | None = None               # {"levels": 3}
    ema: dict | None = None                # {"window": 50}
    sma: dict | None = None                # {"window": 200}
    zscore: dict | None = None             # {"window": 500, "on": "mid"}
    vwap: dict | None = None               # {"bucket": "day" | "tick"}


class MetricsRequest(BaseModel):
    products: list[str] | None = None
    ts_range: tuple[int, int] | None = None
    compute: MetricOptions = MetricOptions()
