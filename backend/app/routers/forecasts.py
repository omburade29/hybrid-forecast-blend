from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query

from app.deps import current_user
from app.models import User
from app.services import runtime
from blender.constants import MODEL_META, REGION_LABELS, SEASONS, VARIABLE_META
from blender.geo import blended_features, point_series

router = APIRouter(prefix="/api/forecasts", tags=["forecasts"])


def _check_variable(variable: str) -> None:
    if variable not in VARIABLE_META:
        raise HTTPException(status_code=400, detail=f"Unknown variable '{variable}'")


def _check_region(region: str) -> None:
    if region not in REGION_LABELS:
        raise HTTPException(status_code=400, detail=f"Unknown region '{region}'")


def _resolve_init(init_time: str | None) -> str:
    cube = runtime.artifacts().cube
    if init_time is None:
        return cube.latest_init()
    if init_time not in cube.init_dates:
        raise HTTPException(status_code=400, detail="Unknown init_time")
    return init_time


def _resolve_lead(lead_hour: int) -> int:
    leads = runtime.artifacts().cube.leads
    if lead_hour not in leads:
        raise HTTPException(status_code=400, detail=f"lead_hour must be one of {leads}")
    return lead_hour


@router.get("/models")
def list_models(_user: User = Depends(current_user)) -> dict:
    score = runtime.artifacts().metrics
    models = []
    for row in MODEL_META:
        nmae = score["normalized_mae"][row["id"]]
        def _normalized(variable: str) -> float:
            block = score["by_variable"][variable]
            stats = block["by_model"][row["id"]]
            mae = stats.get("mae_bias_corrected", stats["mae"])
            return float(mae) / float(block["truth_std"])

        best_var = min(score["by_variable"], key=_normalized)
        models.append({**row, "normalized_mae": round(nmae, 4), "strongest_variable": best_var})
    return {
        "models": models,
        "blend": {
            "id": "BLEND",
            "name": "Adaptive blend",
            "color": "#e11d48",
            "normalized_mae": round(score["blend_normalized_mae"], 4),
            "improvement_pct_vs_best": round(score["improvement_pct_vs_best_normalized"], 2),
            "best_single_model": score["best_model_normalized"],
        },
    }


@router.get("/blended")
def blended_forecast(
    variable: str = Query("rainfall"),
    lead_hour: int = Query(24),
    region: str = Query("india"),
    init_time: str | None = Query(None),
    _user: User = Depends(current_user),
) -> dict:
    _check_variable(variable)
    _check_region(region)
    init_time = _resolve_init(init_time)
    lead_hour = _resolve_lead(lead_hour)
    current = runtime.artifacts()
    payload = blended_features(current, init_time, lead_hour, variable, region)
    day = current.cube.index_of_date(init_time)
    valid = datetime.fromisoformat(init_time) + timedelta(hours=lead_hour)
    payload.update(
        {
            "lead_hour": lead_hour,
            "init_time": init_time,
            "valid_time": valid.strftime("%Y-%m-%dT%H:%MZ"),
            "season": current.cube.seasons[int(current.cube.season_index[day])],
            "region": region,
            "region_label": REGION_LABELS[region],
            "regime": current.cube.regime[day],
            "available_inits": sorted(current.cube.init_dates, reverse=True),
            "leads": list(current.cube.leads),
            "seasons": list(SEASONS),
        }
    )
    return payload


@router.get("/series")
def forecast_series(
    variable: str = Query("rainfall"),
    lat: float = Query(...),
    lon: float = Query(...),
    init_time: str | None = Query(None),
    _user: User = Depends(current_user),
) -> dict:
    _check_variable(variable)
    init_time = _resolve_init(init_time)
    return point_series(runtime.artifacts(), init_time, lat, lon, variable)
