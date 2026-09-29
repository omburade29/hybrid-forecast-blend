"""Hybrid AI–NWP forecast blending API."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

logger = logging.getLogger("uvicorn.error")
_DEV_JWT_SECRET = "development-only-please-change-me!!"
_production = os.getenv("ENVIRONMENT", "").lower() in {"production", "prod"}
from app.database import SessionLocal, init_db
from app.models import User
from app.routers import auth, extremes, forecasts, jobs, metrics, weights
from app.security import hash_password
from app.services import runtime


def _seed_user() -> None:
    db = SessionLocal()
    try:
        email = settings.demo_email.lower()
        if db.query(User).filter(User.email == email).one_or_none() is None:
            db.add(
                User(
                    email=email,
                    full_name=settings.demo_name,
                    password_hash=hash_password(settings.demo_password),
                )
            )
            db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if settings.jwt_secret == _DEV_JWT_SECRET:
        logger.warning("JWT_SECRET is the development default. Set a long random secret before a public deployment.")
    init_db()
    _seed_user()
    runtime.startup()
    yield
    runtime.shutdown()


app = FastAPI(
    title="Hybrid AI–NWP Forecast Blending API",
    description="Adaptive consensus of NWP, AI, and ensemble forecasts, with skill maps and extreme-weather guidance.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None if _production else "/docs",
    redoc_url=None if _production else "/redoc",
    openapi_url=None if _production else "/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(forecasts.router)
app.include_router(weights.router)
app.include_router(metrics.router)
app.include_router(extremes.router)
app.include_router(jobs.router)


@app.get("/api/health")
def health() -> dict:
    ready = runtime._artifacts is not None
    latest = runtime.artifacts().cube.latest_init() if ready else None
    return {"status": "ok" if ready else "starting", "latest_init": latest}
