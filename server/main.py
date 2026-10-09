from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional
import httpx
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from server.db import get_db, init_db
from server.routers import admin, auth, items, market, points, session
from server.schemas import ErrorResponse, HealthResponse
from server.settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB tables on startup
    init_db()
    yield


app = FastAPI(
    title="TG Trails API",
    description="Server-authoritative backend for outdoor movement, verified item drops, points ledger & local open-weight AI missions.",
    version="0.1.0",
    lifespan=lifespan
)

# CORS middleware for local development & tunnels
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, dict):
        return JSONResponse(status_code=exc.status_code, content=detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error_code": "HTTP_ERROR", "message": str(detail)}
    )


# Include Routers
app.include_router(auth.router)
app.include_router(session.router)
app.include_router(items.router)
app.include_router(points.router)
app.include_router(market.router)
app.include_router(admin.router)


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    settings = get_settings()
    db_ok = False
    try:
        with get_db() as conn:
            conn.execute("SELECT 1;").fetchone()
            db_ok = True
    except Exception:
        db_ok = False

    ollama_reachable = False
    try:
        async with httpx.AsyncClient(timeout=1.5) as client:
            resp = await client.get(f"{settings.ollama_base_url}/api/tags")
            if resp.status_code == 200:
                ollama_reachable = True
    except Exception:
        ollama_reachable = False

    overall_status = "healthy" if (db_ok and ollama_reachable) else ("degraded" if db_ok else "unhealthy")

    return HealthResponse(
        status=overall_status,
        version=settings.game_config.app.version,
        db_ok=db_ok,
        ollama_reachable=ollama_reachable,
        ollama_model=settings.ollama_model,
        active_connections=1 if db_ok else 0
    )


# Mount static web frontend if directory exists
web_dir = Path(__file__).resolve().parent.parent / "web"
if web_dir.exists():
    app.mount("/", StaticFiles(directory=str(web_dir), html=True), name="web")
