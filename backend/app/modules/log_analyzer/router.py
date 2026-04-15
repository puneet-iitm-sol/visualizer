from __future__ import annotations

import polars as pl
from fastapi import APIRouter, File, HTTPException, UploadFile

from app.core.errors import IMCError
from app.core.session import store
from app.modules.log_analyzer import compare as compare_mod
from app.modules.log_analyzer import replay as replay_mod
from app.modules.log_analyzer.dashboard import build_dashboard
from app.modules.log_analyzer.ingest import ingest_logs
from app.modules.log_analyzer.inspector import inspect
from app.modules.log_analyzer.positions import build_positions
from app.modules.log_analyzer.schemas import CompareRequest, DashboardRequest, SandboxQuery
from app.schemas.common import ok

router = APIRouter(prefix="/api/logs", tags=["log-analyzer"])


@router.post("/sessions")
def create_session():
    s = store.new_log()
    return ok({"session_id": s.session_id})


@router.post("/sessions/{sid}/upload")
async def upload(sid: str, files: list[UploadFile] = File(...)):
    s = store.get_log(sid)
    payload: list[tuple[str, bytes]] = []
    for f in files:
        payload.append((f.filename or "upload.log", await f.read()))

    try:
        result = ingest_logs(payload)
    except IMCError as e:
        raise HTTPException(status_code=e.status, detail={"code": e.code, "message": e.message})
    except Exception as e:
        raise HTTPException(status_code=422, detail={"code": "parse_error", "message": str(e)})

    s.activities = result.activities.lazy() if result.activities.height else None
    s.trade_history = result.trade_history.lazy() if result.trade_history.height else None
    s.sandbox = result.sandbox.lazy() if result.sandbox.height else None

    positions_df = build_positions(result.trade_history) if result.trade_history.height else None
    s.positions = positions_df.lazy() if positions_df is not None and positions_df.height else None

    # Meta
    products: list[str] = []
    if result.activities.height and "product" in result.activities.columns:
        products = sorted(
            result.activities.select(pl.col("product").cast(pl.Utf8))
                  .to_series().drop_nulls().unique().to_list()
        )
    ts_range: list[int] | None = None
    if result.activities.height:
        ts_range = [int(result.activities["timestamp"].min()), int(result.activities["timestamp"].max())]

    s.meta = {
        "products": products,
        "timestamp_range": ts_range,
        "sandbox_lines": int(result.sandbox.height),
        "activities_rows": int(result.activities.height),
        "trade_history_rows": int(result.trade_history.height),
    }
    s.file_reports = [r.__dict__ for r in result.reports]

    return ok({"files": s.file_reports, **s.meta})


@router.get("/sessions/{sid}/meta")
def meta(sid: str):
    s = store.get_log(sid)
    return ok({
        **s.meta,
        "has_activities": s.activities is not None,
        "has_trade_history": s.trade_history is not None,
        "has_sandbox": s.sandbox is not None,
    })


@router.post("/sessions/{sid}/dashboard")
def dashboard(sid: str, req: DashboardRequest):
    s = store.get_log(sid)
    return ok(build_dashboard(
        s.activities, s.positions, s.trade_history,
        filters=req.filters, target_points=req.target_points,
    ))


@router.get("/sessions/{sid}/state")
def state(sid: str, ts: int):
    s = store.get_log(sid)
    return ok(inspect(
        positions=s.positions, trades=s.trade_history,
        sandbox=s.sandbox, activities=s.activities, ts=ts,
    ))


@router.get("/sessions/{sid}/sandbox")
def sandbox(sid: str, q: str | None = None, ts_from: int | None = None, ts_to: int | None = None,
            limit: int = 500, offset: int = 0):
    s = store.get_log(sid)
    if s.sandbox is None:
        return ok({"rows": [], "total": 0})

    lf = s.sandbox
    if ts_from is not None:
        lf = lf.filter(pl.col("timestamp") >= ts_from)
    if ts_to is not None:
        lf = lf.filter(pl.col("timestamp") <= ts_to)
    if q:
        lf = lf.filter(pl.col("text").str.contains(q, literal=True))

    total = lf.select(pl.len()).collect().item()
    rows = lf.sort(["timestamp", "line_no"], nulls_last=True).slice(offset, limit).collect().to_dicts()
    return ok({"rows": rows, "total": int(total)})


@router.get("/sessions/{sid}/replay")
def replay(sid: str, ts: int | None = None, direction: int = 0):
    """
    direction =  0 → frame at `ts`
    direction =  1 → frame at next tick after `ts`
    direction = -1 → frame at previous tick before `ts`
    """
    s = store.get_log(sid)
    idx = replay_mod.timestamp_index(s.activities)
    if direction != 0:
        ts = replay_mod.step(index=idx, current_ts=ts, direction=direction)
        if ts is None:
            return ok({"ts": None, "at_boundary": True})
    elif ts is None:
        ts = idx[0] if idx else None
    if ts is None:
        return ok({"ts": None, "at_boundary": True})

    return ok(replay_mod.frame_at(
        activities=s.activities, positions=s.positions,
        trades=s.trade_history, sandbox=s.sandbox, ts=ts,
    ))


@router.post("/compare")
def compare_sessions(req: CompareRequest):
    if len(req.session_ids) < 2:
        raise HTTPException(status_code=400, detail="need at least 2 session ids")
    sessions = [store.get_log(sid) for sid in req.session_ids]
    return ok(compare_mod.compare(sessions, target_points=req.target_points))
