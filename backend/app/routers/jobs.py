from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import current_user
from app.models import BlendJob, User
from app.schemas import JobResponse
from app.services import runtime

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def _dump(job: BlendJob) -> JobResponse:
    return JobResponse(
        id=job.id,
        status=job.status,
        trigger=job.trigger,
        init_time=job.init_time,
        message=job.message,
        log=job.log,
        started_at=job.started_at,
        finished_at=job.finished_at,
    )


@router.get("")
def list_jobs(_user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    rows = db.query(BlendJob).order_by(BlendJob.started_at.desc()).limit(50).all()
    return {
        "schedule": f"Every {settings.schedule_hours} hours",
        "scheduler_enabled": not settings.disable_scheduler,
        "jobs": [_dump(row) for row in rows],
    }


@router.post("/run", response_model=JobResponse)
def run_now(_user: User = Depends(current_user)) -> JobResponse:
    job = runtime.execute_blend_job(trigger="manual")
    return _dump(job)


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: str, _user: User = Depends(current_user), db: Session = Depends(get_db)) -> JobResponse:
    job = db.query(BlendJob).filter(BlendJob.id == job_id).one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return _dump(job)
