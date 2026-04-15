from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.errors import IMCError
from app.modules.log_analyzer.router import router as log_router
from app.modules.market_data.router import router as market_router
from app.schemas.common import err, ok

app = FastAPI(title=settings.app_name, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(IMCError)
async def imc_error_handler(request: Request, exc: IMCError):
    return JSONResponse(
        status_code=exc.status,
        content=err(exc.code, exc.message, details=exc.details, status=exc.status),
    )


@app.get("/api/health")
def health():
    return ok({"status": "ok", "app": settings.app_name})


app.include_router(market_router)
app.include_router(log_router)
