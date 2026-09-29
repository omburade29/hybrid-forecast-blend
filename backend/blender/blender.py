"""Combine bias-corrected model forecasts with adaptive weights."""

from __future__ import annotations

import numpy as np

from blender.synthetic import ForecastCube


def bias_correct(cube: ForecastCube, bias: np.ndarray) -> np.ndarray:
    """Subtract the training bias for each date's season.

    `bias` shape: (season, lead, lat, lon, variable, model)
    returns corrected forecasts with the same shape as `cube.forecasts`.
    """
    return cube.forecasts - bias[cube.season_index]


def combine(corrected: np.ndarray, weights: np.ndarray, season_index: np.ndarray, variables: list[str]) -> np.ndarray:
    """Weighted mean of bias-corrected forecasts.

    corrected: (date, lead, lat, lon, variable, model)
    weights:   (season, lead, lat, lon, variable, model)
    returns:   (date, lead, lat, lon, variable)
    """
    applied = weights[season_index]
    blended = np.sum(corrected * applied, axis=-1)
    if "rainfall" in variables:
        blended[..., variables.index("rainfall")] = np.clip(blended[..., variables.index("rainfall")], 0.0, None)
    if "wind_speed" in variables:
        blended[..., variables.index("wind_speed")] = np.clip(blended[..., variables.index("wind_speed")], 0.0, None)
    return blended


def combine_direction(directions: np.ndarray, weights: np.ndarray, season_index: np.ndarray, var_index: int) -> np.ndarray:
    """Weighted vector mean of wind direction (degrees FROM).

    Direction weights follow the wind-speed weights for the same cell and lead.
    """
    applied = weights[season_index, :, :, :, var_index, :]  # (date, lead, lat, lon, model)
    radians = np.deg2rad(directions)
    east = np.sum(applied * np.sin(radians), axis=-1)
    north = np.sum(applied * np.cos(radians), axis=-1)
    return np.mod(np.rad2deg(np.arctan2(east, north)), 360.0)
