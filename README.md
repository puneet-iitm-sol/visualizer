# IMC Prosperity Suite

Two-module workspace for IMC Prosperity 4 — market-data analysis and submission-log debugging.

## Layout

```
backend/   FastAPI + Polars   (port 8000)
frontend/  Next.js 14 App Router + ECharts (port 3000)
```

## Backend

```bash
cd backend
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

or
python -m uvicorn app.main:app --reload --port 8000
```

Smoke tests:
```bash
python tests/test_parsers.py
python tests/test_api.py
```

## Frontend

```bash
cd frontend
npm install
npm run dev      # http://localhost:3000  (proxies /api/* → :8000)
npm run typecheck
```

## Modules

| Route | Purpose |
|---|---|
| `/market-data` | Upload `prices_round_*` + `trades_round_*` CSVs. Cross-filtered ECharts (price + 3-level depth + volume + spread + cumulative PnL + microprice + WOBI). Click any chart point to open the right-side microstructure panel (book + ±5 ctx + tick metrics). |
| `/log-analyzer` | Upload submission `.log` files. Algo PnL, position tracker, sandbox log viewer with keyword filter, state inspector, replay bar (▶/⏸/⏭/⏮ with 1–20× speeds). Drop a second `.log` to overlay a comparison and surface position divergences. |

## Environment

- `IMC_DATA_DIR` — backend session/spill directory (default `.data/`)
- `IMC_MAX_UPLOAD_MB` — per-request upload cap (default 512)
- `NEXT_PUBLIC_API_BASE` — frontend → backend URL (default uses `next.config.mjs` rewrites to `127.0.0.1:8000`)
