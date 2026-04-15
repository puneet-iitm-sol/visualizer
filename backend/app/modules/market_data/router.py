from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.core.errors import IMCError
from app.core.session import store
from app.modules.market_data import parser
from app.modules.market_data.filters import apply as apply_filters
from app.modules.market_data.joiner import build_unified
from app.modules.market_data.metrics import compute_all
from app.modules.market_data.query import build_series
from app.modules.market_data.schemas import MetricsRequest, QueryRequest
from app.modules.market_data.snapshots import snapshot
from app.schemas.common import ok

router = APIRouter(prefix="/api/market", tags=["market-data"])


@router.post("/sessions")
def create_session():
    s = store.new_market()
    return ok({"session_id": s.session_id})


@router.post("/sessions/{sid}/upload")
async def upload(sid: str, files: list[UploadFile] = File(...)):
    s = store.get_market(sid)
    payload: list[tuple[str, bytes]] = []
    for f in files:
        payload.append((f.filename or "uploaded.csv", await f.read()))

    try:
        result = parser.ingest(payload)
    except IMCError as e:
        raise HTTPException(status_code=e.status, detail={"code": e.code, "message": e.message, "details": e.details})
    except Exception as e:
        raise HTTPException(status_code=422, detail={"code": "parse_error", "message": str(e)})

    s.prices = result.prices
    s.trades = result.trades
    if result.prices is not None:
        s.unified = build_unified(result.prices, result.trades)
    s.meta = {
        "products": result.products,
        "days": result.days,
        "timestamp_range": list(result.timestamp_range) if result.timestamp_range else None,
    }

    return ok({
        "files": [r.__dict__ for r in result.reports],
        "products": result.products,
        "days": result.days,
        "timestamp_range": list(result.timestamp_range) if result.timestamp_range else None,
    })


@router.get("/sessions/{sid}/meta")
def meta(sid: str):
    s = store.get_market(sid)
    return ok({
        **s.meta,
        "has_prices": s.prices is not None,
        "has_trades": s.trades is not None,
    })


@router.post("/sessions/{sid}/query")
def query(sid: str, req: QueryRequest):
    s = store.get_market(sid)
    if s.unified is None:
        raise HTTPException(status_code=400, detail="no prices uploaded yet")
    lf = apply_filters(s.unified, req.filters)
    return ok(build_series(lf, s.trades, series=req.series, downsample=req.downsample))


@router.get("/sessions/{sid}/snapshot")
def snapshot_endpoint(sid: str, ts: int, product: str, day: int | None = None, context: int = 5):
    s = store.get_market(sid)
    if s.unified is None:
        raise HTTPException(status_code=400, detail="no prices uploaded yet")
    return ok(snapshot(s.unified, s.trades, timestamp=ts, product=product, day=day, context=context))


@router.post("/sessions/{sid}/metrics")
def metrics(sid: str, req: MetricsRequest):
    s = store.get_market(sid)
    if s.unified is None:
        raise HTTPException(status_code=400, detail="no prices uploaded yet")

    lf = s.unified
    if req.products:
        import polars as pl
        lf = lf.filter(pl.col("product").cast(pl.Utf8).is_in(req.products))
    if req.ts_range is not None:
        import polars as pl
        lo, hi = req.ts_range
        lf = lf.filter(pl.col("timestamp").is_between(lo, hi, closed="both"))

    c = req.compute
    lf = compute_all(
        lf,
        microprice_on=c.microprice,
        wobi_levels=(c.wobi or {}).get("levels") if c.wobi else None,
        ema_window=(c.ema or {}).get("window") if c.ema else None,
        sma_window=(c.sma or {}).get("window") if c.sma else None,
        zscore_window=(c.zscore or {}).get("window") if c.zscore else None,
        zscore_on=(c.zscore or {}).get("on", "mid_price") if c.zscore else "mid_price",
        vwap_bucket=(c.vwap or {}).get("bucket") if c.vwap else None,
    )

    df = lf.sort(["product", "day", "timestamp"]).collect()
    return ok({"rows": df.height, "columns": df.columns, "head": df.head(200).to_dicts()})
