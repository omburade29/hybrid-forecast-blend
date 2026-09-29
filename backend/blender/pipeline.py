"""Train weights and build the operational artifacts kept in memory."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np

from blender.blender import bias_correct, combine, combine_direction
from blender.data_loader import load_forecast_cube
from blender.extremes import extreme_probability
from blender.metrics import score_cube
from blender.skill_estimator import estimate_skill
from blender.synthetic import ForecastCube
from blender.weight_model import AdaptiveWeightModel, train_weight_model


@dataclass
class Artifacts:
    cube: ForecastCube
    bias: np.ndarray
    mae: np.ndarray
    rmse: np.ndarray
    weight_model: AdaptiveWeightModel
    corrected: np.ndarray
    blended: np.ndarray
    wind_direction: np.ndarray
    metrics: dict
    trained_at: str

    @property
    def weights(self) -> np.ndarray:
        return self.weight_model.weights


def build_artifacts() -> Artifacts:
    """Full training pass. Deterministic and fast enough to run at API startup."""
    cube = load_forecast_cube()
    skill = estimate_skill(cube)
    weight_model = train_weight_model(cube, skill["mae"])
    corrected = bias_correct(cube, skill["bias"])
    blended = combine(corrected, weight_model.weights, cube.season_index, cube.variables)
    wind_index = cube.variables.index("wind_speed")
    direction = combine_direction(cube.wind_dir_forecasts, weight_model.weights, cube.season_index, wind_index)
    metrics = score_cube(cube, corrected, blended, region="india")
    return Artifacts(
        cube=cube,
        bias=skill["bias"],
        mae=skill["mae"],
        rmse=skill["rmse"],
        weight_model=weight_model,
        corrected=corrected,
        blended=blended,
        wind_direction=direction,
        metrics=metrics,
        trained_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    )


def operational_summary(artifacts: Artifacts, init_time: str | None = None) -> str:
    """Human-readable log for a blending job."""
    cube = artifacts.cube
    init_time = init_time or cube.latest_init()
    day = cube.index_of_date(init_time)
    season = cube.seasons[int(cube.season_index[day])]
    lines = [
        f"Cycle {init_time} 00Z  season={season}  regime={cube.regime[day]}",
        f"Models: {', '.join(cube.models)}",
        f"Grid: {cube.lats.size} x {cube.lons.size}  leads: {', '.join(str(v) for v in cube.leads)}",
        f"Weight model: skill softmax + linear gating ({artifacts.weight_model.skill_fraction:.0%} skill table)",
        f"Trained at {artifacts.trained_at}",
    ]
    score = artifacts.metrics
    lines.append(
        "Held-out normalized MAE "
        f"blend={score['blend_normalized_mae']:.3f}  "
        f"best model {score['best_model_normalized']}={score['normalized_mae'][score['best_model_normalized']]:.3f}  "
        f"improvement={score['improvement_pct_vs_best_normalized']:.1f}%"
    )
    from blender.constants import HAZARDS

    for lead in (24, 48, 72):
        lead_i = cube.leads.index(lead)
        parts = []
        for hazard, spec in HAZARDS.items():
            fields = extreme_probability(
                artifacts.corrected[day],
                artifacts.weights[int(cube.season_index[day])],
                artifacts.mae[int(cube.season_index[day])],
                hazard,
            )
            probability = fields["probability"][lead_i]
            elevated = int(np.sum(probability >= 0.5))
            parts.append(f"{spec['title']} {elevated}")
        rain = artifacts.blended[day, lead_i, :, :, cube.variables.index("rainfall")]
        lines.append(
            f"T+{lead:03d}h  domain-mean rain {float(rain.mean()):.1f} mm  "
            f"max {float(rain.max()):.1f} mm  elevated cells: " + ", ".join(parts)
        )
    lines.append("Status: succeeded")
    return "\n".join(lines)
