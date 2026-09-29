from fastapi import APIRouter, Depends, HTTPException, Query

from app.deps import current_user
from app.models import User
from app.services import runtime
from blender.constants import REGION_LABELS, SEASONS, VARIABLE_META
from blender.geo import weight_features

router = APIRouter(prefix="/api/weights", tags=["weights"])


@router.get("/maps")
def weight_maps(
    variable: str = Query("rainfall"),
    lead_hour: int = Query(72),
    season: str = Query("JJAS"),
    region: str = Query("india"),
    _user: User = Depends(current_user),
) -> dict:
    if variable not in VARIABLE_META:
        raise HTTPException(status_code=400, detail=f"Unknown variable '{variable}'")
    if season not in SEASONS:
        raise HTTPException(status_code=400, detail=f"season must be one of {SEASONS}")
    if region not in REGION_LABELS:
        raise HTTPException(status_code=400, detail=f"Unknown region '{region}'")
    leads = runtime.artifacts().cube.leads
    if lead_hour not in leads:
        raise HTTPException(status_code=400, detail=f"lead_hour must be one of {leads}")
    return weight_features(runtime.artifacts(), season, lead_hour, variable, region)
