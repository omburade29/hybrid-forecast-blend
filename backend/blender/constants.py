"""Shared constants for the hybrid blending system.

Extension point: add a new model or variable here, then teach
`synthetic.py` (or your real-data loader) to fill the corresponding axis.
"""

from __future__ import annotations

MODELS: list[str] = ["GFS", "ECMWF", "AI-A", "AI-B", "ENS"]

# Linear variables scored with MAE / RMSE. Wind direction is stored separately
# and blended with a weighted vector mean (see blender.combine_direction).
VARIABLES: list[str] = ["rainfall", "tmin", "tmax", "wind_speed"]

LEADS: list[int] = [0, 24, 48, 72, 96, 120, 144, 168]

SEASONS: list[str] = ["DJF", "MAM", "JJAS", "ON"]

VARIABLE_META: dict[str, dict[str, str]] = {
    "rainfall": {"label": "Rainfall", "unit": "mm", "kind": "accumulated"},
    "tmin": {"label": "Minimum temperature", "unit": "°C", "kind": "instant"},
    "tmax": {"label": "Maximum temperature", "unit": "°C", "kind": "instant"},
    "wind_speed": {"label": "Wind speed", "unit": "m/s", "kind": "instant"},
}

MODEL_META: list[dict[str, str]] = [
    {
        "id": "GFS",
        "name": "GFS",
        "family": "NWP",
        "center": "NOAA / NCEP",
        "color": "#2563eb",
        "description": "Global spectral NWP. Competitive at short range; skill falls off faster with lead time, with a warm daytime bias over northern plains.",
    },
    {
        "id": "ECMWF",
        "name": "ECMWF IFS",
        "family": "NWP",
        "center": "ECMWF",
        "color": "#059669",
        "description": "High-resolution global NWP. Best large-scale skill at longer leads. Tends to under-forecast orographic monsoon rainfall.",
    },
    {
        "id": "AI-A",
        "name": "AI-Model-A",
        "family": "AI/ML",
        "center": "Data-driven global",
        "color": "#d97706",
        "description": "Graph-style AI weather model. Excellent temperature skill, but regresses heavy rain and high wind toward climatology.",
    },
    {
        "id": "AI-B",
        "name": "AI-Model-B",
        "family": "AI/ML",
        "center": "Data-driven regional",
        "color": "#7c3aed",
        "description": "AI model tuned for monsoon rainfall. Strong in JJAS rain, weaker for winter temperature and wind.",
    },
    {
        "id": "ENS",
        "name": "Ensemble mean",
        "family": "Ensemble",
        "center": "Multi-model mean",
        "color": "#0891b2",
        "description": "Smoothed ensemble mean. Stable and low-bias, but under-represents extremes.",
    },
]

BLEND_COLOR = "#e11d48"

# Coarse India domain. Each cell is the center of a ~3° tile.
LATS_START, LATS_END, N_LAT = 8.0, 35.0, 10
LONS_START, LONS_END, N_LON = 68.0, 97.0, 10

# (south, north, west, east) in degrees, inclusive of cell centers.
REGIONS: dict[str, tuple[float, float, float, float]] = {
    "india": (6.0, 38.0, 66.0, 99.0),
    "north": (24.0, 36.5, 72.0, 88.0),
    "south": (7.5, 16.5, 74.0, 84.5),
    "west": (16.0, 26.5, 67.5, 78.0),
    "east": (18.0, 27.5, 82.0, 90.5),
    "northeast": (22.0, 30.5, 88.0, 98.0),
}

REGION_LABELS: dict[str, str] = {
    "india": "All India",
    "north": "North India",
    "south": "South India",
    "west": "West India",
    "east": "East India",
    "northeast": "Northeast India",
}

# Days per season in the synthetic archive. The last N_TEST of each season
# are held out for evaluation; biases and weights see only the training days.
DAYS_PER_SEASON = 40
N_TEST = 10

HAZARDS: dict[str, dict[str, object]] = {
    "heavy_rain": {
        "title": "Heavy rainfall",
        "variable": "rainfall",
        "threshold": 64.5,
        "unit": "mm",
        "comparator": ">=",
        "scale": 22.0,
        "summary": (
            "Chance that daily rainfall reaches the IMD heavy-rain threshold of 64.5 mm. "
            "Probability combines the blended value, each model's historical error, and how strongly the models agree."
        ),
    },
    "heat_wave": {
        "title": "Heat wave",
        "variable": "tmax",
        "threshold": 40.0,
        "unit": "°C",
        "comparator": ">=",
        "scale": 1.8,
        "summary": (
            "Chance that maximum temperature reaches 40 °C. This is a simplified plains heat-wave screen. "
            "Operational IMD criteria also use departures from normal and persist for consecutive days."
        ),
    },
    "high_wind": {
        "title": "High wind",
        "variable": "wind_speed",
        "threshold": 15.0,
        "unit": "m/s",
        "comparator": ">=",
        "scale": 2.5,
        "summary": (
            "Chance that wind speed reaches 15 m/s (about 54 km/h), a damaging-wind screen for this demo. "
            "Real warning criteria depend on gusts, exposure, and local climatology."
        ),
    },
}
