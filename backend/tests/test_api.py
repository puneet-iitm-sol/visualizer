"""End-to-end FastAPI smoke test — exercises every endpoint in both modules.

Run with:
    cd backend
    python tests/test_api.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from app.main import app
from tests.test_parsers import LOG_FILE, PRICES_CSV, TRADES_CSV

client = TestClient(app)


def _must_ok(r, label: str) -> dict:
    assert r.status_code == 200, f"{label}: HTTP {r.status_code} body={r.text}"
    body = r.json()
    assert body["ok"] is True, f"{label}: ok=False body={body}"
    return body["data"]


def test_market_flow() -> None:
    sid = _must_ok(client.post("/api/market/sessions"), "create market")["session_id"]

    up = _must_ok(
        client.post(
            f"/api/market/sessions/{sid}/upload",
            files=[
                ("files", ("prices_round_1_day_0.csv", PRICES_CSV.encode(), "text/csv")),
                ("files", ("trades_round_1_day_0_nn.csv", TRADES_CSV.encode(), "text/csv")),
            ],
        ),
        "market upload",
    )
    assert "KELP" in up["products"]
    assert up["timestamp_range"] == [0, 100]

    meta = _must_ok(client.get(f"/api/market/sessions/{sid}/meta"), "market meta")
    assert meta["has_prices"] and meta["has_trades"]

    q = _must_ok(
        client.post(
            f"/api/market/sessions/{sid}/query",
            json={
                "filters": {"products": ["KELP"]},
                "series": ["mid", "spread", "volume", "pnl", "trades", "microprice", "wobi"],
                "downsample": {"target_points": 1000, "method": "lttb"},
            },
        ),
        "market query",
    )
    assert "KELP" in q["series"]["mid"]
    assert "KELP" in q["series"]["wobi"]
    assert q["series"]["trades"]["KELP"][0]["qty"] == 5

    snap = _must_ok(
        client.get(
            f"/api/market/sessions/{sid}/snapshot",
            params={"ts": 100, "product": "KELP", "context": 3},
        ),
        "market snapshot",
    )
    assert snap["book"]["bids"][0][0] == 2029
    assert snap["metrics"]["microprice"] is not None

    m = _must_ok(
        client.post(
            f"/api/market/sessions/{sid}/metrics",
            json={"products": ["KELP"], "compute": {"microprice": True, "wobi": {"levels": 3}}},
        ),
        "market metrics",
    )
    assert m["rows"] == 2

    print("[ok] market API — sid", sid)


def test_log_flow() -> None:
    sid = _must_ok(client.post("/api/logs/sessions"), "create log")["session_id"]

    up = _must_ok(
        client.post(
            f"/api/logs/sessions/{sid}/upload",
            files=[("files", ("round1.log", LOG_FILE.encode(), "text/plain"))],
        ),
        "log upload",
    )
    assert up["activities_rows"] == 2 and up["trade_history_rows"] == 2

    meta = _must_ok(client.get(f"/api/logs/sessions/{sid}/meta"), "log meta")
    assert meta["has_activities"] and meta["has_trade_history"] and meta["has_sandbox"]

    dash = _must_ok(
        client.post(f"/api/logs/sessions/{sid}/dashboard", json={}),
        "log dashboard",
    )
    assert "KELP" in dash["algo_pnl"]
    assert "KELP" in dash["executions"] or "RAINFOREST_RESIN" in dash["executions"]

    st = _must_ok(client.get(f"/api/logs/sessions/{sid}/state", params={"ts": 100}), "log state")
    # SUBMISSION bought 5 KELP at ts=100 → position should be +5
    assert st["positions"].get("KELP", 0) == 5
    assert any(row["timestamp"] is not None for row in st["sandbox_window"])

    sbx = _must_ok(
        client.get(f"/api/logs/sessions/{sid}/sandbox", params={"q": "KELP"}),
        "log sandbox",
    )
    assert sbx["total"] >= 1

    rp = _must_ok(
        client.get(f"/api/logs/sessions/{sid}/replay", params={"ts": 0, "direction": 1}),
        "log replay step",
    )
    assert rp["ts"] == 100

    # Compare endpoint with a second session
    sid2 = _must_ok(client.post("/api/logs/sessions"), "create log 2")["session_id"]
    _must_ok(
        client.post(
            f"/api/logs/sessions/{sid2}/upload",
            files=[("files", ("round1b.log", LOG_FILE.encode(), "text/plain"))],
        ),
        "log upload 2",
    )
    cmp = _must_ok(
        client.post("/api/logs/compare", json={"session_ids": [sid, sid2]}),
        "log compare",
    )
    assert set(cmp["sids"]) == {sid, sid2}
    # identical uploads ⇒ no divergence
    assert cmp["divergences"] == []

    print("[ok] log API — sid", sid)


if __name__ == "__main__":
    test_market_flow()
    test_log_flow()
    print("\nall API smoke tests passed.")
