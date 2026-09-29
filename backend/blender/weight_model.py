"""Adaptive forecast weights.

Two pieces are combined:

1. Skill table — a softmax over historical MAE for every
   (season, lead, grid cell, variable). This is what makes the weight maps
   change across India and across lead time.
2. Gating network — a small multinomial logistic regression on lead time,
   latitude, longitude, season, and variable. It is a mixture-of-experts gate
   trained to match the skill-table targets.

`AdaptiveWeightModel` is the extension point. Swap `fit` / `predict` for a
gradient-boosted model or a neural gate without changing `blender.py`.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from blender.synthetic import ForecastCube


def softmax(logits: np.ndarray, axis: int = -1) -> np.ndarray:
    shifted = logits - np.max(logits, axis=axis, keepdims=True)
    exp = np.exp(shifted)
    return exp / np.sum(exp, axis=axis, keepdims=True)


def weights_from_mae(mae: np.ndarray, sharpness: float = 0.45) -> np.ndarray:
    """Turn per-model MAE into weights that sum to 1 along the last axis.

    `sharpness` scales the softmax temperature relative to the median MAE.
    Smaller values trust the local winner more; larger values blend more evenly.
    """
    scale = np.median(mae, axis=-1, keepdims=True)
    temperature = np.maximum(scale * sharpness, 1e-3)
    return softmax(-mae / temperature)


@dataclass
class GatingNet:
    """Linear mixture-of-experts gate. Weights W have shape (features, models)."""

    W: np.ndarray
    b: np.ndarray

    @staticmethod
    def features(
        season_i: int,
        lead_norm: float,
        lat_norm: float,
        lon_norm: float,
        var_i: int,
        n_seasons: int,
        n_vars: int,
    ) -> np.ndarray:
        season = np.zeros(n_seasons, dtype=np.float64)
        season[season_i] = 1.0
        variable = np.zeros(n_vars, dtype=np.float64)
        variable[var_i] = 1.0
        return np.concatenate([np.array([lead_norm, lat_norm, lon_norm], dtype=np.float64), season, variable])

    @classmethod
    def fit(cls, features: np.ndarray, target: np.ndarray, epochs: int = 350, lr: float = 0.25, l2: float = 1e-3) -> "GatingNet":
        rng = np.random.default_rng(7)
        n_samples, n_features = features.shape
        n_models = target.shape[1]
        weight = rng.normal(0.0, 0.01, size=(n_features, n_models))
        bias = np.zeros(n_models, dtype=np.float64)
        for _ in range(epochs):
            probs = softmax(features @ weight + bias)
            grad_logits = (probs - target) / n_samples
            weight -= lr * (features.T @ grad_logits + l2 * weight)
            bias -= lr * grad_logits.sum(axis=0)
        return cls(W=weight, b=bias)

    def predict(self, features: np.ndarray) -> np.ndarray:
        return softmax(features @ self.W + self.b)


@dataclass
class AdaptiveWeightModel:
    """Final weights used by the blender. Shape (season, lead, lat, lon, variable, model)."""

    weights: np.ndarray
    skill_weights: np.ndarray
    gate_weights: np.ndarray
    gating: GatingNet
    skill_fraction: float = 0.86

    def save(self, path: str) -> None:
        np.savez_compressed(
            path,
            weights=self.weights,
            skill_weights=self.skill_weights,
            gate_weights=self.gate_weights,
            W=self.gating.W,
            b=self.gating.b,
            skill_fraction=np.array([self.skill_fraction]),
        )

    @classmethod
    def load(cls, path: str) -> "AdaptiveWeightModel":
        data = np.load(path)
        gating = GatingNet(W=data["W"], b=data["b"])
        return cls(
            weights=data["weights"],
            skill_weights=data["skill_weights"],
            gate_weights=data["gate_weights"],
            gating=gating,
            skill_fraction=float(data["skill_fraction"][0]),
        )


def train_weight_model(cube: ForecastCube, mae: np.ndarray, sharpness: float = 0.42) -> AdaptiveWeightModel:
    skill_weights = weights_from_mae(mae, sharpness=sharpness)

    n_season, n_lead, n_lat, n_lon, n_var, n_model = skill_weights.shape
    lat_span = float(cube.lats.max() - cube.lats.min()) or 1.0
    lon_span = float(cube.lons.max() - cube.lons.min()) or 1.0
    max_lead = float(max(cube.leads)) or 1.0

    samples = n_season * n_lead * n_lat * n_lon * n_var
    features = np.empty((samples, 3 + n_season + n_var), dtype=np.float64)
    target = np.empty((samples, n_model), dtype=np.float64)
    cursor = 0
    for season_i in range(n_season):
        for lead_i, lead in enumerate(cube.leads):
            for lat_i, lat in enumerate(cube.lats):
                for lon_i, lon in enumerate(cube.lons):
                    for var_i in range(n_var):
                        features[cursor] = GatingNet.features(
                            season_i,
                            lead / max_lead,
                            (float(lat) - float(cube.lats.min())) / lat_span,
                            (float(lon) - float(cube.lons.min())) / lon_span,
                            var_i,
                            n_season,
                            n_var,
                        )
                        target[cursor] = skill_weights[season_i, lead_i, lat_i, lon_i, var_i]
                        cursor += 1

    gating = GatingNet.fit(features, target)
    gate_weights = gating.predict(features).reshape(skill_weights.shape)

    skill_fraction = 0.86
    mixed = skill_fraction * skill_weights + (1.0 - skill_fraction) * gate_weights
    mixed = np.clip(mixed, 1e-6, None)
    mixed /= mixed.sum(axis=-1, keepdims=True)
    return AdaptiveWeightModel(
        weights=mixed,
        skill_weights=skill_weights,
        gate_weights=gate_weights,
        gating=gating,
        skill_fraction=skill_fraction,
    )
