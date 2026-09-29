"""Persistence for users, the published skill scorecard, and blending jobs."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), default="")
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SkillMetric(Base):
    """One row of the operational scorecard persisted after each blending run."""

    __tablename__ = "skill_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_name: Mapped[str] = mapped_column(String(32), index=True)
    variable: Mapped[str] = mapped_column(String(32), index=True)
    season: Mapped[str] = mapped_column(String(16), default="ALL")
    lead_hour: Mapped[int] = mapped_column(Integer, default=-1)
    region: Mapped[str] = mapped_column(String(32), default="india")
    mae: Mapped[float] = mapped_column(Float)
    rmse: Mapped[float] = mapped_column(Float, default=0.0)
    crps: Mapped[float] = mapped_column(Float, default=0.0)
    bias: Mapped[float] = mapped_column(Float, default=0.0)
    mae_bias_corrected: Mapped[float | None] = mapped_column(Float, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class BlendJob(Base):
    __tablename__ = "blend_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    status: Mapped[str] = mapped_column(String(16), index=True)
    trigger: Mapped[str] = mapped_column(String(16))
    init_time: Mapped[str] = mapped_column(String(32), default="")
    message: Mapped[str] = mapped_column(String(400), default="")
    log: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
