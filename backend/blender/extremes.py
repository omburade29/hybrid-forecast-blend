"""Extreme-weather probabilities from the blended ensemble.

Each bias-corrected member is treated as the mean of a Gaussian whose spread
is that member's historical MAE at the same season, lead, and grid cell.
Member probabilities are averaged with the same adaptive weights used for the
deterministic blend. Confidence is high when the members agree.

This is a guidance product. Rainfall is skewed, so the Gaussian tail is only
an approximation — replace `member_probability` with a trained extreme model
or an ensemble CDF when real ensemble members are available.
"""

from __future__ import annotations

import numpy as np

from blender.constants import HAZARDS


def _norm_cdf(z: np.ndarray) -> np.ndarray:
    """Standard normal CDF via a Hastings approximation (no SciPy dependency)."""
    t = 1.0 / (1.0 + 0.2316419 * np.abs(z))
    density = 0.3989423 * np.exp(-0.5 * np.square(z))
    polynomial = t * (0.319381530 + t * (-0.356563782 + t * (1.781477937 + t * (-1.821255978 + t * 1.330274429))))
    tail = density * polynomial
    return np.where(z >= 0.0, 1.0 - tail, tail)


def member_probability(forecast: np.ndarray, sigma: np.ndarray, threshold: float) -> np.ndarray:
    safe_sigma = np.maximum(sigma, 1e-3)
    return 1.0 - _norm_cdf((threshold - forecast) / safe_sigma)


def extreme_probability(
    corrected: np.ndarray,
    weights: np.ndarray,
    mae: np.ndarray,
    hazard: str,
) -> dict[str, np.ndarray]:
    """Probability and confidence for one date.

    corrected: (lead, lat, lon, variable, model) already sliced to one date
    weights:   (lead, lat, lon, variable, model) for that date's season
    mae:       (lead, lat, lon, variable, model)
    Returns arrays shaped (lead, lat, lon).
    """
    spec = HAZARDS[hazard]
    var_name = str(spec["variable"])
    # Local import avoids a constants/variables cycle at module import for typing only.
    from blender.constants import VARIABLES

    var_index = VARIABLES.index(var_name)
    threshold = float(spec["threshold"])
    floor = {"rainfall": 3.0, "tmin": 0.4, "tmax": 0.4, "wind_speed": 0.5}[var_name]
    sigma = np.maximum(mae[:, :, :, var_index, :], floor)
    forecast = corrected[:, :, :, var_index, :]
    per_model = member_probability(forecast, sigma, threshold)
    model_weights = weights[:, :, :, var_index, :]
    probability = np.clip(np.sum(model_weights * per_model, axis=-1), 0.0, 1.0)
    confidence = np.clip(1.0 - np.std(per_model, axis=-1) / 0.35, 0.0, 1.0)
    return {"probability": probability, "confidence": confidence, "per_model": per_model}
