from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import current_user
from app.models import SkillMetric, User
from app.services import runtime
from blender.constants import REGION_LABELS, VARIABLE_META

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("/skill")
def skill(
    variable: str | None = Query(None),
    region: str = Query("india"),
    _user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    if variable is not None and variable not in VARIABLE_META:
        raise HTTPException(status_code=400, detail=f"Unknown variable '{variable}'")
    if region not in REGION_LABELS:
        raise HTTPException(status_code=400, detail=f"Unknown region '{region}'")
    try:
        payload = runtime.metrics_for(variable, region)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    stored = (
        db.query(SkillMetric)
        .filter(SkillMetric.variable == (variable or "NORMALIZED"), SkillMetric.lead_hour == -1, SkillMetric.season == "ALL")
        .count()
    )
    payload["persisted_rows"] = stored
    payload["scorecard_rows"] = db.query(SkillMetric).count()
    return payload
