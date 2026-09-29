"""Historical skill: bias, MAE, and RMSE by model, season, lead, and grid cell.

All statistics are estimated on the training split only. The returned bias is
later removed before weighting so a model is not punished twice for a stable offset.
"""

from __future__ import annotations

import numpy as np

from blender.synthetic import ForecastCube


def _smooth_latlon(array: np.ndarray) -> np.ndarray:
    """Smooth axes (lat=1, lon=2) of an array shaped (lead, lat, lon, ...)."""

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

    return blur(blur(array, 2), 1)


def estimate_skill(cube: ForecastCube) -> dict[str, np.ndarray]:
    """Return bias, MAE, and RMSE on training dates.

    Shapes are (season, lead, lat, lon, variable, model).
    """
    error = cube.forecasts - cube.truth[..., None]
    n_season = len(cube.seasons)
    bias = np.zeros((n_season,) + error.shape[1:], dtype=np.float64)
    mae = np.zeros_like(bias)
    rmse = np.zeros_like(bias)

    train = cube.split == 0
    for season_i in range(n_season):
        mask = train & (cube.season_index == season_i)
        sample = error[mask]
        season_bias = sample.mean(axis=0)
        residual = sample - season_bias
        season_mae = np.abs(residual).mean(axis=0)
        season_rmse = np.sqrt(np.square(residual).mean(axis=0))

        # Share strength with neighbouring cells and with the domain mean so
        # weights are not fit to a handful of noisy grid points.
        season_mae = _smooth_latlon(season_mae)
        domain = season_mae.mean(axis=(1, 2), keepdims=True)
        season_mae = 0.55 * season_mae + 0.45 * domain

        bias[season_i] = season_bias
        mae[season_i] = np.maximum(season_mae, 1e-3)
        rmse[season_i] = season_rmse

    return {"bias": bias, "mae": mae, "rmse": rmse}
