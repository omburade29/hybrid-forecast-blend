"""Process-wide forecast engine and the operational blending job.

The numpy archive lives in memory. Skill summaries and job history are written
to the database so they survive a restart only as a published scorecard — the
next startup retrains from the deterministic archive (or from FORECAST_DIR).

To move scheduled work to Celery, keep `execute_blend_job` as the task body
and enqueue it instead of calling it from APScheduler.
"""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import BlendJob, SkillMetric
from blender.metrics import score_cube
from blender.pipeline import Artifacts, build_artifacts, operational_summary

_lock = threading.Lock()
_artifacts: Artifacts | None = None
_scheduler: BackgroundScheduler | None = None


def artifacts() -> Artifacts:
    if _artifacts is None:
        raise RuntimeError("Forecast engine is not ready")
    return _artifacts


def startup() -> None:
    global _artifacts
    with _lock:
        _artifacts = build_artifacts()
    _persist_metrics(_artifacts)
    _record(trigger="startup", status="succeeded", message="Startup blend completed", log=operational_summary(_artifacts))
    if not settings.disable_scheduler:
        _start_scheduler()


def shutdown() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None


def _start_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        return
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(
        lambda: execute_blend_job(trigger="schedule"),
        "interval",
        hours=max(1, settings.schedule_hours),
        id="operational-blend",
        replace_existing=True,
    )
    scheduler.start()
    _scheduler = scheduler


def execute_blend_job(trigger: str = "manual") -> BlendJob:
    """Retrain weights on the current archive and publish a new scorecard.

    Synchronous on purpose: a synthetic cycle finishes in about a second.
    A production deployment should queue this function on a worker.
    """
    global _artifacts
    job_id = str(uuid.uuid4())
    started = datetime.now(timezone.utc)
    with _lock:
        try:
            built = build_artifacts()
            _artifacts = built
            log = operational_summary(built)
            _persist_metrics(built)
            return _record(
                trigger=trigger,
                status="succeeded",
                message=f"Blended cycle {built.cube.latest_init()} 00Z",
                log=log,
                job_id=job_id,
                started=started,
                init_time=built.cube.latest_init(),
            )
        except Exception as exc:  # noqa: BLE001 — job status must capture any failure
            return _record(
                trigger=trigger,
                status="failed",
                message=str(exc),
                log=f"Blend failed: {exc}",
                job_id=job_id,
                started=started,
                init_time="",
            )


def metrics_for(variable: str | None, region: str) -> dict:
    current = artifacts()
    if region == "india" and current.metrics.get("region") == "india":
        score = current.metrics
    else:
        score = score_cube(current.cube, current.corrected, current.blended, region=region)
    if variable is None:
        return score
    if variable not in score["by_variable"]:
        raise KeyError(variable)
    return {
        "region": region,
        "variable": variable,
        "normalized_mae": current.metrics["normalized_mae"] if region == "india" else score["normalized_mae"],
        "improvement_pct_vs_best_normalized": score["improvement_pct_vs_best_normalized"],
        "best_model_normalized": score["best_model_normalized"],
        "blend_normalized_mae": score["blend_normalized_mae"],
        "crps_note": score["crps_note"],
        "ensemble_crps_normalized": score["ensemble_crps_normalized"].get(variable),
        **score["by_variable"][variable],
    }


def _persist_metrics(built: Artifacts) -> None:
    score = built.metrics
    now = datetime.now(timezone.utc)
    rows: list[SkillMetric] = []
    for model, value in score["normalized_mae"].items():
        rows.append(
            SkillMetric(
                model_name=model,
                variable="NORMALIZED",
                season="ALL",
                lead_hour=-1,
                region="india",
                mae=float(value),
                rmse=float(value),
                crps=float(value),
                bias=0.0,
                mae_bias_corrected=float(value),
                updated_at=now,
            )
        )
    for variable, block in score["by_variable"].items():
        for model, stats in block["by_model"].items():
            rows.append(
                SkillMetric(
                    model_name=model,
                    variable=variable,
                    season="ALL",
                    lead_hour=-1,
                    region="india",
                    mae=stats["mae"],
                    rmse=stats["rmse"],
                    crps=stats["crps"],
                    bias=stats["bias"],
                    mae_bias_corrected=stats.get("mae_bias_corrected", stats["mae"]),
                    updated_at=now,
                )
            )
        for lead_row in block["by_lead"]:
            for model, stats in lead_row["models"].items():
                rows.append(
                    SkillMetric(
                        model_name=model,
                        variable=variable,
                        season="ALL",
                        lead_hour=int(lead_row["lead_hour"]),
                        region="india",
                        mae=stats["mae"],
                        rmse=stats.get("mae_bias_corrected", stats["mae"]),
                        crps=stats["mae"],
                        bias=0.0,
                        mae_bias_corrected=stats.get("mae_bias_corrected", stats["mae"]),
                        updated_at=now,
                    )
                )
        for season_row in block["by_season"]:
            for model, stats in season_row["models"].items():
                rows.append(
                    SkillMetric(
                        model_name=model,
                        variable=variable,
                        season=season_row["season"],
                        lead_hour=-1,
                        region="india",
                        mae=stats["mae"],
                        rmse=stats.get("mae_bias_corrected", stats["mae"]),
                        crps=stats["mae"],
                        bias=0.0,
                        mae_bias_corrected=stats.get("mae_bias_corrected", stats["mae"]),
                        updated_at=now,
                    )
                )
    db: Session = SessionLocal()
    try:
        db.query(SkillMetric).delete()
        db.add_all(rows)
        db.commit()
    finally:
        db.close()


def _record(
    trigger: str,
    status: str,
    message: str,
    log: str,
    job_id: str | None = None,
    started: datetime | None = None,
    init_time: str | None = None,
) -> BlendJob:
    now = datetime.now(timezone.utc)
    job = BlendJob(
        id=job_id or str(uuid.uuid4()),
        status=status,
        trigger=trigger,
        init_time=init_time if init_time is not None else (artifacts().cube.latest_init() if _artifacts else ""),
        message=message[:400],
        log=log,
        started_at=started or now,
        finished_at=now,
    )
    db = SessionLocal()
    try:
        db.add(job)
        db.commit()
        db.refresh(job)
        db.expunge(job)
        return job
    finally:
        db.close()
