from fastapi import APIRouter, Depends, HTTPException, Query

from app.deps import current_user
from app.models import User
from app.services import runtime
from blender.constants import HAZARDS, REGION_LABELS
from blender.geo import extreme_features, extremes_overview

router = APIRouter(prefix="/api/extremes", tags=["extremes"])


def _init(init_time: str | None) -> str:
    cube = runtime.artifacts().cube
    if init_time is None:
        return cube.latest_init()
    if init_time not in cube.init_dates:
        raise HTTPException(status_code=400, detail="Unknown init_time")
    return init_time


@router.get("/overview")
def overview(
    region: str = Query("india"),
    init_time: str | None = Query(None),
    _user: User = Depends(current_user),
) -> dict:
    if region not in REGION_LABELS:
        raise HTTPException(status_code=400, detail=f"Unknown region '{region}'")
    return extremes_overview(runtime.artifacts(), _init(init_time), region)


@router.get("")
def guidance(
    hazard: str = Query("heavy_rain"),
    lead_hour: int = Query(24),
    region: str = Query("india"),
    init_time: str | None = Query(None),
    _user: User = Depends(current_user),
) -> dict:
    if hazard not in HAZARDS:
        raise HTTPException(status_code=400, detail=f"hazard must be one of {list(HAZARDS)}")
    if region not in REGION_LABELS:
        raise HTTPException(status_code=400, detail=f"Unknown region '{region}'")
    leads = runtime.artifacts().cube.leads
    if lead_hour not in leads:
        raise HTTPException(status_code=400, detail=f"lead_hour must be one of {leads}")
    init_time = _init(init_time)
    payload = extreme_features(runtime.artifacts(), init_time, lead_hour, hazard, region)
    payload["lead_hour"] = lead_hour
    payload["init_time"] = init_time
    payload["region"] = region
    payload["leads"] = list(leads)
    payload["caveat"] = (
        "Probabilities are guidance from a Gaussian residual model fit on synthetic history. "
        "They are not a calibrated warning product until the archive is replaced with real forecasts and observations."
    )
    return payload
