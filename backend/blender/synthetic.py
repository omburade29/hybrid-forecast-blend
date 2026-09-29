"""Deterministic synthetic NWP / AI / ensemble forecast archive.

The generator is built so that model skill depends on region, season, and
lead time, and so that model errors are negatively correlated. That is the
situation adaptive blending is designed for: no single model wins everywhere,
and a weighted consensus beats each member.

Replace this module with a GRIB/NetCDF reader by returning the same
`ForecastCube` from `data_loader.load_forecast_cube`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np

from blender.constants import (
    DAYS_PER_SEASON,
    LATS_END,
    LATS_START,
    LEADS,
    LONS_END,
    LONS_START,
    MODELS,
    N_LAT,
    N_LON,
    N_TEST,
    SEASONS,
    VARIABLES,
)

# Relative short-range error. Axis order: model, variable, season.
# Lower means a more skillful model. Seasons: DJF, MAM, JJAS, ON.
# Variables: rainfall, tmin, tmax, wind_speed.
_SHORT = np.array(
    [
        # GFS — solid short range, weaker monsoon rain and hot-season tmax
        [
            [0.62, 0.55, 0.88, 0.66],
            [0.50, 0.46, 0.55, 0.48],
            [0.55, 0.52, 0.78, 0.58],
            [0.58, 0.52, 0.70, 0.60],
        ],
        # ECMWF — best large-scale model, especially at longer leads
        [
            [0.46, 0.42, 0.50, 0.44],
            [0.36, 0.34, 0.40, 0.36],
            [0.38, 0.36, 0.44, 0.38],
            [0.42, 0.40, 0.48, 0.43],
        ],
        # AI-A — excellent temperature, conservative on rain and wind
        [
            [0.85, 0.78, 0.70, 0.80],
            [0.30, 0.28, 0.32, 0.30],
            [0.28, 0.27, 0.34, 0.29],
            [0.82, 0.76, 0.88, 0.80],
        ],
        # AI-B — monsoon rain specialist, weaker in winter
        [
            [0.95, 0.62, 0.40, 0.70],
            [0.62, 0.50, 0.42, 0.52],
            [0.66, 0.52, 0.40, 0.55],
            [0.90, 0.78, 0.72, 0.84],
        ],
        # Ensemble mean — moderate and smooth
        [
            [0.58, 0.54, 0.56, 0.55],
            [0.44, 0.42, 0.46, 0.44],
            [0.46, 0.44, 0.52, 0.46],
            [0.52, 0.50, 0.58, 0.52],
        ],
    ],
    dtype=np.float64,
)

# How fast random error grows per 72 hours of lead time.
_GROWTH = np.array([0.70, 0.32, 0.48, 0.58, 0.38], dtype=np.float64)

# Constant bias (model, variable, season) in physical units.
_BIAS = np.zeros((len(MODELS), len(VARIABLES), len(SEASONS)), dtype=np.float64)
_BIAS[0, 2, :] = 0.9  # GFS warm tmax
_BIAS[0, 0, 2] = 4.0  # GFS wet monsoon
_BIAS[1, 0, 2] = -3.0  # ECMWF dry monsoon
_BIAS[1, 2, 1] = -0.4
_BIAS[3, 1, 0] = -0.8  # AI-B cold winter nights
_BIAS[4, 0, :] = -1.0  # ensemble mean slightly dry

_BASE_SIGMA = np.array([8.0, 1.35, 1.55, 1.7], dtype=np.float64)
_ERROR_SIGNS = np.array([1.0, -0.9, 0.25, -0.55, 0.05], dtype=np.float64)


@dataclass
class ForecastCube:
    """In-memory forecast archive.

    truth:      (date, lead, lat, lon, variable)
    forecasts:  (date, lead, lat, lon, variable, model)
    wind_dir_*: degrees, meteorological (direction the wind blows FROM)
    split:      0 = train, 1 = test
    """

    models: list[str]
    variables: list[str]
    seasons: list[str]
    leads: list[int]
    lats: np.ndarray
    lons: np.ndarray
    init_dates: list[str]
    season_index: np.ndarray
    split: np.ndarray
    regime: list[str]
    truth: np.ndarray
    forecasts: np.ndarray
    wind_dir_truth: np.ndarray
    wind_dir_forecasts: np.ndarray

    @property
    def n_models(self) -> int:
        return len(self.models)

    def index_of_date(self, init_time: str) -> int:
        try:
            return self.init_dates.index(init_time)
        except ValueError as exc:
            raise KeyError(f"Unknown init_time {init_time}") from exc

    def latest_init(self) -> str:
        return max(self.init_dates)


def season_of_month(month: int) -> str:
    if month in (12, 1, 2):
        return "DJF"
    if month in (3, 4, 5):
        return "MAM"
    if month in (6, 7, 8, 9):
        return "JJAS"
    return "ON"


def _climatology(lat: np.ndarray, lon: np.ndarray, season: str) -> np.ndarray:
    """Seasonal mean field, shape (lat, lon, variable)."""
    rain_factor = {"DJF": 0.18, "MAM": 0.45, "JJAS": 1.0, "ON": 0.50}[season]
    ghats = np.exp(-((lon - 75.5) ** 2) / (2 * 2.5**2) - ((lat - 14.0) ** 2) / (2 * 4.2**2))
    northeast = np.exp(-((lon - 93.0) ** 2) / (2 * 3.0**2) - ((lat - 26.0) ** 2) / (2 * 3.2**2))
    desert = np.exp(-((lon - 72.0) ** 2) / (2 * 5.0**2) - ((lat - 26.5) ** 2) / (2 * 4.0**2))
    rain = (1.4 + 22.0 * ghats + 30.0 * northeast) * rain_factor * (1.0 - 0.72 * desert)
    rain = np.clip(rain, 0.3, None)

    season_tmax = {"DJF": -7.0, "MAM": 6.0, "JJAS": 1.5, "ON": 0.4}[season]
    plains = np.exp(-((lon - 76.5) ** 2) / (2 * 7.5**2) - ((lat - 26.5) ** 2) / (2 * 5.5**2))
    coastal = np.exp(-((lon - 73.5) ** 2) / (2 * 5.5**2)) * np.clip((22.0 - lat) / 14.0, 0.0, 1.0)
    tmax = 29.5 + season_tmax + 8.0 * plains - 3.2 * coastal - 0.30 * (lat - 22.0)
    tmin = tmax - (8.5 + 4.0 * np.clip((lat - 24.0) / 10.0, 0.0, 1.0) + (2.5 if season == "DJF" else 0.0))

    wind_factor = {"DJF": 0.7, "MAM": 1.25, "JJAS": 1.05, "ON": 0.85}[season]
    wind = (3.0 + 2.8 * ghats + 2.4 * coastal + 1.4 * desert) * wind_factor
    return np.stack([rain, tmin, tmax, wind], axis=-1)


def _smooth_spatial(array: np.ndarray) -> np.ndarray:
    """3-tap edge-padded smoother on the lat (axis -3) and lon (axis -2) dimensions.

    Input layout is (..., lat, lon, channel). Channel may be missing.
    """

    def blur(values: np.ndarray, axis: int) -> np.ndarray:
        pad = [(0, 0)] * values.ndim
        pad[axis] = (1, 1)
        padded = np.pad(values, pad, mode="edge")
        prev = [slice(None)] * values.ndim
        mid = [slice(None)] * values.ndim
        nxt = [slice(None)] * values.ndim
        prev[axis] = slice(0, -2)
        mid[axis] = slice(1, -1)
        nxt[axis] = slice(2, None)
        return (padded[tuple(prev)] + padded[tuple(mid)] + padded[tuple(nxt)]) / 3.0

    # lat is -3 when a channel axis exists, otherwise -2. Callers pass channelled arrays.
    return blur(blur(array, -2), -3)


def _date_list(season: str) -> list[str]:
    # JJAS block ends on the demo "today" so the latest operational cycle is current.
    start = {
        "DJF": date(2025, 1, 5),
        "MAM": date(2025, 4, 2),
        "JJAS": date(2026, 9, 27) - timedelta(days=DAYS_PER_SEASON - 1),
        "ON": date(2025, 10, 3),
    }[season]
    return [(start + timedelta(days=i)).isoformat() for i in range(DAYS_PER_SEASON)]


def _classify_regime(mean_rain: float, mean_tmax: float, mean_wind: float, season: str) -> str:
    if mean_rain >= 12 and season == "JJAS":
        return "active_monsoon"
    if mean_tmax >= 36:
        return "heat_dominant"
    if mean_wind >= 9:
        return "windy"
    if mean_rain < 2.5:
        return "dry_fair"
    return "transitional"


def _inject_events(
    truth: np.ndarray,
    season: str,
    rng: np.random.Generator,
    lats: np.ndarray,
    lons: np.ndarray,
) -> None:
    """Add coherent rain, heat, and wind events so extreme guidance is not empty."""
    lat_grid, lon_grid = np.meshgrid(lats, lons, indexing="ij")
    n_dates, n_leads, n_lat, _n_lon, _n_var = truth.shape
    rain_rate = 0.62 if season == "JJAS" else 0.20
    for day in range(n_dates):
        for lead in range(n_leads):
            if rng.random() < rain_rate:
                i = int(rng.integers(0, n_lat))
                j = int(rng.integers(0, lons.size))
                amp = float(rng.uniform(55, 170 if season == "JJAS" else 100))
                blob = np.exp(
                    -((lat_grid - lats[i]) ** 2) / (2 * 3.0**2) - ((lon_grid - lons[j]) ** 2) / (2 * 3.0**2)
                )
                truth[day, lead, :, :, 0] += amp * blob
            if season in ("MAM", "JJAS") and rng.random() < 0.40:
                i = int(rng.integers(n_lat // 2, n_lat))
                j = int(rng.integers(0, max(1, lons.size // 2)))
                blob = np.exp(
                    -((lat_grid - lats[i]) ** 2) / (2 * 4.0**2) - ((lon_grid - lons[j]) ** 2) / (2 * 4.0**2)
                )
                bump = float(rng.uniform(3.5, 7.5))
                truth[day, lead, :, :, 2] += bump * blob
                truth[day, lead, :, :, 1] += 0.45 * bump * blob
            if rng.random() < (0.28 if season in ("MAM", "ON", "JJAS") else 0.12):
                i = int(rng.integers(0, n_lat))
                j = int(rng.integers(0, lons.size))
                blob = np.exp(
                    -((lat_grid - lats[i]) ** 2) / (2 * 3.4**2) - ((lon_grid - lons[j]) ** 2) / (2 * 3.4**2)
                )
                truth[day, lead, :, :, 3] += float(rng.uniform(9, 20)) * blob
    truth[..., 0] = np.clip(truth[..., 0], 0.0, 450.0)
    truth[..., 3] = np.clip(truth[..., 3], 0.0, 48.0)


def generate_cube(seed: int = 42) -> ForecastCube:
    """Build the full synthetic archive. Results are deterministic for a given seed."""
    rng = np.random.default_rng(seed)
    lats = np.linspace(LATS_START, LATS_END, N_LAT)
    lons = np.linspace(LONS_START, LONS_END, N_LON)
    lat_grid, lon_grid = np.meshgrid(lats, lons, indexing="ij")

    init_dates: list[str] = []
    season_ids: list[int] = []
    for season_i, season in enumerate(SEASONS):
        days = _date_list(season)
        init_dates.extend(days)
        season_ids.extend([season_i] * len(days))

    n_dates = len(init_dates)
    n_leads = len(LEADS)
    n_var = len(VARIABLES)
    n_model = len(MODELS)
    truth = np.empty((n_dates, n_leads, N_LAT, N_LON, n_var), dtype=np.float64)
    forecasts = np.empty((n_dates, n_leads, N_LAT, N_LON, n_var, n_model), dtype=np.float64)
    wind_dir_truth = np.empty((n_dates, n_leads, N_LAT, N_LON), dtype=np.float64)
    wind_dir_forecasts = np.empty((n_dates, n_leads, N_LAT, N_LON, n_model), dtype=np.float64)

    lead_hours = np.asarray(LEADS, dtype=np.float64)
    lead_mult = 1.0 + _GROWTH[None, :] * (lead_hours[:, None] / 72.0)  # (lead, model)

    for season_i, season in enumerate(SEASONS):
        d0 = season_i * DAYS_PER_SEASON
        d1 = d0 + DAYS_PER_SEASON
        climo = _climatology(lat_grid, lon_grid, season)  # (lat, lon, var)

        synoptic = rng.standard_normal((DAYS_PER_SEASON, n_leads, N_LAT, N_LON, n_var))
        synoptic = _smooth_spatial(synoptic)
        block = np.empty_like(synoptic)
        block[..., 0] = np.clip(climo[..., 0] * np.exp(0.42 * synoptic[..., 0]), 0.0, 350.0)
        block[..., 1] = climo[..., 1] + 1.25 * synoptic[..., 1]
        block[..., 2] = climo[..., 2] + 1.45 * synoptic[..., 2]
        block[..., 3] = np.clip(climo[..., 3] + 1.15 * synoptic[..., 3], 0.0, 28.0)
        _inject_events(block, season, rng, lats, lons)
        truth[d0:d1] = block

        common = _smooth_spatial(rng.standard_normal((DAYS_PER_SEASON, n_leads, N_LAT, N_LON, n_var)))
        idiosyncratic = rng.standard_normal((DAYS_PER_SEASON, n_leads, N_LAT, N_LON, n_var, n_model))
        # Negatively correlated common mode, then scale by each model's sigma.
        standardized = _ERROR_SIGNS * 0.95 * common[..., None] + 0.50 * idiosyncratic

        short = _SHORT[:, :, season_i].T  # (var, model)
        hetero = np.ones((DAYS_PER_SEASON, n_leads, N_LAT, N_LON, n_var, n_model))
        hetero[..., 0, :] = (0.50 + block[..., 0] / 48.0)[..., None]
        sigma = (
            _BASE_SIGMA[None, None, None, None, :, None]
            * short[None, None, None, None, :, :]
            * lead_mult[None, :, None, None, None, :]
            * hetero
        )

        spatial = np.zeros((N_LAT, N_LON, n_var, n_model), dtype=np.float64)
        spatial[..., 2, 0] = 0.7 * ((lat_grid - 22.0) / 10.0)  # GFS warmer to the north
        ghats = np.exp(-((lon_grid - 75.5) ** 2) / (2 * 2.5**2) - ((lat_grid - 14.0) ** 2) / (2 * 4.2**2))
        spatial[..., 0, 1] = -6.0 * ghats  # ECMWF dry along the Western Ghats
        spatial[..., 0, 4] = -2.0 * ghats

        bias = _BIAS[:, :, season_i].T  # (var, model)
        raw = block[..., None] + bias + spatial + standardized * sigma

        # AI-A (index 2) damps rain and wind extremes toward climatology.
        raw[..., 0, 2] = 0.50 * raw[..., 0, 2] + 0.50 * climo[..., 0]
        raw[..., 3, 2] = 0.58 * raw[..., 3, 2] + 0.42 * climo[..., 3]
        # Ensemble mean (index 4) is a damped copy of the member average plus its own error.
        member_mean = raw[..., :4].mean(axis=-1)
        raw[..., 4] = 0.72 * member_mean + 0.28 * raw[..., 4]

        raw[..., 0, :] = np.clip(raw[..., 0, :], 0.0, None)
        raw[..., 3, :] = np.clip(raw[..., 3, :], 0.0, None)
        forecasts[d0:d1] = raw

        base_dir = {"DJF": 45.0, "MAM": 310.0, "JJAS": 255.0, "ON": 70.0}[season]
        dir_noise = _smooth_spatial(rng.standard_normal((DAYS_PER_SEASON, n_leads, N_LAT, N_LON, 1)))[..., 0]
        wind_dir_truth[d0:d1] = np.mod(base_dir + 18.0 * np.sin(np.deg2rad(lat_grid)) + 12.0 * dir_noise, 360.0)
        dir_err = rng.normal(0.0, 1.0, size=(DAYS_PER_SEASON, n_leads, N_LAT, N_LON, n_model))
        dir_sigma = (np.array([22.0, 14.0, 18.0, 26.0, 16.0]) * lead_mult)[None, :, None, None, :]
        wind_dir_forecasts[d0:d1] = np.mod(wind_dir_truth[d0:d1, ..., None] + dir_err * dir_sigma, 360.0)

    season_index = np.asarray(season_ids, dtype=np.int64)
    split = np.zeros(n_dates, dtype=np.int64)
    for season_i in range(len(SEASONS)):
        d1 = (season_i + 1) * DAYS_PER_SEASON
        split[d1 - N_TEST : d1] = 1

    regimes: list[str] = []
    for day, season_i in enumerate(season_index):
        # Lead index 1 is T+24h, a representative synoptic snapshot.
        regimes.append(
            _classify_regime(
                float(truth[day, 1, :, :, 0].mean()),
                float(truth[day, 1, :, :, 2].mean()),
                float(truth[day, 1, :, :, 3].mean()),
                SEASONS[int(season_i)],
            )
        )

    return ForecastCube(
        models=list(MODELS),
        variables=list(VARIABLES),
        seasons=list(SEASONS),
        leads=list(LEADS),
        lats=lats,
        lons=lons,
        init_dates=init_dates,
        season_index=season_index,
        split=split,
        regime=regimes,
        truth=truth,
        forecasts=forecasts,
        wind_dir_truth=wind_dir_truth,
        wind_dir_forecasts=wind_dir_forecasts,
    )
