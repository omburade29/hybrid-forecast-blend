"""GeoJSON builders for forecast, weight, and extreme maps."""

from __future__ import annotations

import numpy as np

from blender.constants import HAZARDS, MODEL_META, REGIONS, VARIABLE_META
from blender.extremes import extreme_probability
from blender.metrics import cell_mask
from blender.pipeline import Artifacts


def _half_steps(axis: np.ndarray) -> float:
    if axis.size < 2:
        return 1.5
    return float(np.median(np.diff(axis)) / 2.0)


def _polygon(lat: float, lon: float, half_lat: float, half_lon: float) -> dict:
    ring = [
        [lon - half_lon, lat - half_lat],
        [lon + half_lon, lat - half_lat],
        [lon + half_lon, lat + half_lat],
        [lon - half_lon, lat + half_lat],
        [lon - half_lon, lat - half_lat],
    ]
    return {"type": "Polygon", "coordinates": [ring]}


def _dominant(weights: dict[str, float]) -> tuple[str, float]:
    model = max(weights, key=weights.get)
    return model, float(weights[model])


def _round_map(values: dict[str, float], digits: int = 3) -> dict[str, float]:
    return {key: round(float(val), digits) for key, val in values.items()}


def feature_collection(features: list[dict]) -> dict:
    return {"type": "FeatureCollection", "features": features}


def blended_features(artifacts: Artifacts, init_time: str, lead_hour: int, variable: str, region: str) -> dict:
    cube = artifacts.cube
    day = cube.index_of_date(init_time)
    lead_i = cube.leads.index(int(lead_hour))
    var_i = cube.variables.index(variable)
    season_i = int(cube.season_index[day])
    mask = cell_mask(cube, region)
    half_lat = _half_steps(cube.lats)
    half_lon = _half_steps(cube.lons)
    colors = {row["id"]: row["color"] for row in MODEL_META}

    features = []
    values = []
    dominant_counts: dict[str, int] = {model: 0 for model in cube.models}
    for lat_i, lat in enumerate(cube.lats):
        for lon_i, lon in enumerate(cube.lons):
            if not mask[lat_i, lon_i]:
                continue
            weights = {
                model: float(artifacts.weights[season_i, lead_i, lat_i, lon_i, var_i, model_i])
                for model_i, model in enumerate(cube.models)
            }
            raw = {
                model: float(cube.forecasts[day, lead_i, lat_i, lon_i, var_i, model_i])
                for model_i, model in enumerate(cube.models)
            }
            corrected = {
                model: float(artifacts.corrected[day, lead_i, lat_i, lon_i, var_i, model_i])
                for model_i, model in enumerate(cube.models)
            }
            blended = float(artifacts.blended[day, lead_i, lat_i, lon_i, var_i])
            winner, winner_w = _dominant(weights)
            dominant_counts[winner] += 1
            values.append(blended)
            features.append(
                {
                    "type": "Feature",
                    "geometry": _polygon(float(lat), float(lon), half_lat, half_lon),
                    "properties": {
                        "lat": round(float(lat), 3),
                        "lon": round(float(lon), 3),
                        "blended": round(blended, 3),
                        "raw": _round_map(raw, 2),
                        "corrected": _round_map(corrected, 2),
                        "weights": _round_map(weights, 3),
                        "dominant_model": winner,
                        "dominant_weight": round(winner_w, 3),
                        "dominant_color": colors.get(winner, "#334155"),
                        "wind_direction": round(float(artifacts.wind_direction[day, lead_i, lat_i, lon_i]), 1),
                    },
                }
            )

    dominant_model = max(dominant_counts, key=dominant_counts.get) if features else None
    meta = VARIABLE_META[variable]
    return {
        "type": "FeatureCollection",
        "features": features,
        "summary": {
            "domain_mean": round(float(np.mean(values)), 3) if values else None,
            "domain_max": round(float(np.max(values)), 3) if values else None,
            "domain_min": round(float(np.min(values)), 3) if values else None,
            "dominant_model": dominant_model,
            "dominant_counts": dominant_counts,
            "cells": len(features),
        },
        "variable": variable,
        "variable_label": meta["label"],
        "unit": meta["unit"],
    }


def weight_features(artifacts: Artifacts, season: str, lead_hour: int, variable: str, region: str) -> dict:
    cube = artifacts.cube
    season_i = cube.seasons.index(season)
    lead_i = cube.leads.index(int(lead_hour))
    var_i = cube.variables.index(variable)
    mask = cell_mask(cube, region)
    half_lat = _half_steps(cube.lats)
    half_lon = _half_steps(cube.lons)
    colors = {row["id"]: row["color"] for row in MODEL_META}
    counts = {model: 0 for model in cube.models}
    features = []
    for lat_i, lat in enumerate(cube.lats):
        for lon_i, lon in enumerate(cube.lons):
            if not mask[lat_i, lon_i]:
                continue
            weights = {
                model: float(artifacts.weights[season_i, lead_i, lat_i, lon_i, var_i, model_i])
                for model_i, model in enumerate(cube.models)
            }
            mae = {
                model: float(artifacts.mae[season_i, lead_i, lat_i, lon_i, var_i, model_i])
                for model_i, model in enumerate(cube.models)
            }
            winner, winner_w = _dominant(weights)
            counts[winner] += 1
            features.append(
                {
                    "type": "Feature",
                    "geometry": _polygon(float(lat), float(lon), half_lat, half_lon),
                    "properties": {
                        "lat": round(float(lat), 3),
                        "lon": round(float(lon), 3),
                        "weights": _round_map(weights, 3),
                        "mae": _round_map(mae, 3),
                        "dominant_model": winner,
                        "dominant_weight": round(winner_w, 3),
                        "dominant_color": colors.get(winner, "#334155"),
                    },
                }
            )
    total = max(1, sum(counts.values()))
    legend = [
        {
            "model": row["id"],
            "name": row["name"],
            "color": row["color"],
            "share": round(counts[row["id"]] / total, 3),
            "cells": counts[row["id"]],
        }
        for row in MODEL_META
    ]
    return {
        "type": "FeatureCollection",
        "features": features,
        "legend": legend,
        "season": season,
        "lead_hour": int(lead_hour),
        "variable": variable,
        "region": region,
    }


def extreme_features(artifacts: Artifacts, init_time: str, lead_hour: int, hazard: str, region: str) -> dict:
    cube = artifacts.cube
    spec = HAZARDS[hazard]
    day = cube.index_of_date(init_time)
    season_i = int(cube.season_index[day])
    lead_i = cube.leads.index(int(lead_hour))
    var_i = cube.variables.index(str(spec["variable"]))
    fields = extreme_probability(
        artifacts.corrected[day],
        artifacts.weights[season_i],
        artifacts.mae[season_i],
        hazard,
    )
    mask = cell_mask(cube, region)
    half_lat = _half_steps(cube.lats)
    half_lon = _half_steps(cube.lons)
    features = []
    probs = []
    for lat_i, lat in enumerate(cube.lats):
        for lon_i, lon in enumerate(cube.lons):
            if not mask[lat_i, lon_i]:
                continue
            probability = float(fields["probability"][lead_i, lat_i, lon_i])
            probs.append(probability)
            features.append(
                {
                    "type": "Feature",
                    "geometry": _polygon(float(lat), float(lon), half_lat, half_lon),
                    "properties": {
                        "lat": round(float(lat), 3),
                        "lon": round(float(lon), 3),
                        "probability": round(probability, 3),
                        "confidence": round(float(fields["confidence"][lead_i, lat_i, lon_i]), 3),
                        "blended_value": round(float(artifacts.blended[day, lead_i, lat_i, lon_i, var_i]), 2),
                        "threshold": spec["threshold"],
                    },
                }
            )
    arr = np.asarray(probs) if probs else np.asarray([0.0])
    return {
        "type": "FeatureCollection",
        "features": features,
        "hazard": hazard,
        "title": spec["title"],
        "explanation": spec["summary"],
        "threshold": spec["threshold"],
        "unit": spec["unit"],
        "comparator": spec["comparator"],
        "variable": spec["variable"],
        "summary": {
            "cells": len(features),
            "elevated": int(np.sum(arr >= 0.5)),
            "high": int(np.sum(arr >= 0.75)),
            "max_probability": round(float(arr.max()), 3),
            "mean_probability": round(float(arr.mean()), 3),
        },
    }


def extremes_overview(artifacts: Artifacts, init_time: str, region: str) -> dict:
    cube = artifacts.cube
    day = cube.index_of_date(init_time)
    season_i = int(cube.season_index[day])
    mask = cell_mask(cube, region)
    hazards = {}
    for hazard in HAZARDS:
        fields = extreme_probability(
            artifacts.corrected[day],
            artifacts.weights[season_i],
            artifacts.mae[season_i],
            hazard,
        )
        probability = fields["probability"][:, mask]
        hazards[hazard] = {
            "title": HAZARDS[hazard]["title"],
            "mean_probability": [round(float(np.mean(probability[lead_i])), 3) for lead_i in range(len(cube.leads))],
            "elevated_fraction": [
                round(float(np.mean(probability[lead_i] >= 0.5)), 3) for lead_i in range(len(cube.leads))
            ],
            "max_probability": [round(float(np.max(probability[lead_i])), 3) for lead_i in range(len(cube.leads))],
        }
    return {"init_time": init_time, "region": region, "leads": list(cube.leads), "hazards": hazards, "regime": cube.regime[day]}


def point_series(artifacts: Artifacts, init_time: str, lat: float, lon: float, variable: str) -> dict:
    cube = artifacts.cube
    lat_i = int(np.argmin(np.abs(cube.lats - lat)))
    lon_i = int(np.argmin(np.abs(cube.lons - lon)))
    day = cube.index_of_date(init_time)
    var_i = cube.variables.index(variable)
    season_i = int(cube.season_index[day])
    models = {}
    weight_series = {}
    for model_i, model in enumerate(cube.models):
        models[model] = [round(float(artifacts.corrected[day, lead_i, lat_i, lon_i, var_i, model_i]), 3) for lead_i in range(len(cube.leads))]
        weight_series[model] = [
            round(float(artifacts.weights[season_i, lead_i, lat_i, lon_i, var_i, model_i]), 3) for lead_i in range(len(cube.leads))
        ]
    blend = [round(float(artifacts.blended[day, lead_i, lat_i, lon_i, var_i]), 3) for lead_i in range(len(cube.leads))]
    direction = [round(float(artifacts.wind_direction[day, lead_i, lat_i, lon_i]), 1) for lead_i in range(len(cube.leads))]
    meta = VARIABLE_META[variable]
    return {
        "lat": round(float(cube.lats[lat_i]), 3),
        "lon": round(float(cube.lons[lon_i]), 3),
        "variable": variable,
        "unit": meta["unit"],
        "variable_label": meta["label"],
        "init_time": init_time,
        "leads": list(cube.leads),
        "blend": blend,
        "models": models,
        "weights": weight_series,
        "wind_direction": direction,
    }


def region_names() -> list[str]:
    return list(REGIONS)
