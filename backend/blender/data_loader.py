"""Load a forecast cube from the synthetic generator or from a directory of arrays.

Real-data extension
-------------------
Set DATA_SOURCE=directory and FORECAST_DIR to a folder containing `cube.npz`
with these arrays:

    truth                float  (date, lead, lat, lon, variable)
    forecasts            float  (date, lead, lat, lon, variable, model)
    season_index         int    (date,)
    split                int    (date,)   0 train, 1 test
    lats                 float  (lat,)
    lons                 float  (lon,)
    init_dates           unicode (date,)  ISO dates
    wind_dir_truth       float  (date, lead, lat, lon)          optional
    wind_dir_forecasts   float  (date, lead, lat, lon, model)   optional
    models               unicode (model,)                       optional
    variables            unicode (variable,)                    optional

Variable order defaults to rainfall, tmin, tmax, wind_speed.
Lead times default to 0, 24, 48, 72, 96, 120, 144, 168 hours.

Typical ETL sources: GFS and ECMWF GRIB via cfgrib/xarray, AI models such as
GraphCast or Pangu from NetCDF, and a truth analysis such as ERA5 or IMD gridded
observations. Regrid every source onto the same lat/lon grid before saving.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np

from blender.constants import LEADS, MODELS, SEASONS, VARIABLES
from blender.synthetic import ForecastCube, generate_cube, season_of_month


def load_forecast_cube() -> ForecastCube:
    source = os.environ.get("DATA_SOURCE", "synthetic").strip().lower()
    if source == "directory":
        folder = Path(os.environ.get("FORECAST_DIR", "./data/forecasts"))
        return _load_directory(folder)
    if source != "synthetic":
        raise ValueError(f"Unknown DATA_SOURCE '{source}'. Use 'synthetic' or 'directory'.")
    return generate_cube()


def _load_directory(folder: Path) -> ForecastCube:
    path = folder / "cube.npz"
    if not path.exists():
        raise FileNotFoundError(
            f"DATA_SOURCE=directory but {path} does not exist. "
            "See data_loader.py for the expected arrays."
        )
    data = np.load(path, allow_pickle=False)
    models = list(data["models"]) if "models" in data.files else list(MODELS)
    variables = list(data["variables"]) if "variables" in data.files else list(VARIABLES)
    init_dates = [str(value) for value in data["init_dates"]]
    n_dates = len(init_dates)
    wind_truth = data["wind_dir_truth"] if "wind_dir_truth" in data.files else np.zeros(data["truth"].shape[:-1])
    if "wind_dir_forecasts" in data.files:
        wind_fcst = data["wind_dir_forecasts"]
    else:
        wind_fcst = np.zeros(data["truth"].shape[:-1] + (len(models),))
    regimes = []
    truth = data["truth"]
    for day in range(n_dates):
        month = int(init_dates[day][5:7])
        rain = float(np.mean(truth[day, min(1, truth.shape[1]), :, :, variables.index("rainfall")]))
        tmax = float(np.mean(truth[day, min(1, truth.shape[1]), :, :, variables.index("tmax")]))
        wind = float(np.mean(truth[day, min(1, truth.shape[1]), :, :, variables.index("wind_speed")]))
        if rain >= 12 and season_of_month(month) == "JJAS":
            regimes.append("active_monsoon")
        elif tmax >= 36:
            regimes.append("heat_dominant")
        elif wind >= 9:
            regimes.append("windy")
        elif rain < 2.5:
            regimes.append("dry_fair")
        else:
            regimes.append("transitional")
    return ForecastCube(
        models=models,
        variables=variables,
        seasons=list(SEASONS),
        leads=list(LEADS),
        lats=np.asarray(data["lats"], dtype=np.float64),
        lons=np.asarray(data["lons"], dtype=np.float64),
        init_dates=init_dates,
        season_index=np.asarray(data["season_index"], dtype=np.int64),
        split=np.asarray(data["split"], dtype=np.int64),
        regime=regimes,
        truth=np.asarray(truth, dtype=np.float64),
        forecasts=np.asarray(data["forecasts"], dtype=np.float64),
        wind_dir_truth=np.asarray(wind_truth, dtype=np.float64),
        wind_dir_forecasts=np.asarray(wind_fcst, dtype=np.float64),
    )
