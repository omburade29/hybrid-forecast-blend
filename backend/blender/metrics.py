"""Held-out skill scores for each model and for the blended forecast.

Individual-model MAE is reported two ways:
  * raw — the forecast as issued
  * bias_corrected — after removing the training-period bias

The blend is always the bias-corrected weighted consensus. Aggregate skill
uses MAE divided by the standard deviation of the truth so rainfall (mm) and
temperature (°C) can be compared.
"""

from __future__ import annotations

import numpy as np

from blender.constants import REGIONS
from blender.synthetic import ForecastCube


def cell_mask(cube: ForecastCube, region: str) -> np.ndarray:
    if region not in REGIONS:
        raise KeyError(f"Unknown region '{region}'")
    south, north, west, east = REGIONS[region]
    lat_ok = (cube.lats[:, None] >= south) & (cube.lats[:, None] <= north)
    lon_ok = (cube.lons[None, :] >= west) & (cube.lons[None, :] <= east)
    return lat_ok & lon_ok


def _apply_cells(values: np.ndarray, mask: np.ndarray) -> np.ndarray:
    shape = (1, 1, mask.shape[0], mask.shape[1]) + (1,) * (values.ndim - 4)
    return np.where(mask.reshape(shape), values, np.nan)


def _pack(mae: float, rmse: float, bias: float, crps: float, mae_bc: float | None = None) -> dict[str, float]:
    row = {"mae": mae, "rmse": rmse, "bias": bias, "crps": crps}
    if mae_bc is not None:
        row["mae_bias_corrected"] = mae_bc
    return row


def score_cube(
    cube: ForecastCube,
    corrected: np.ndarray,
    blended: np.ndarray,
    region: str = "india",
) -> dict:
    """Compute the scorecard used by the API, the database, and the UI."""
    mask = cell_mask(cube, region)
    test = cube.split == 1
    truth = _apply_cells(cube.truth[test], mask)
    raw = _apply_cells(cube.forecasts[test], mask)
    bc = _apply_cells(corrected[test], mask)
    blend = _apply_cells(blended[test], mask)
    seasons = cube.season_index[test]

    # truth std per variable, over every held-out sample in the region.
    truth_std = np.nanstd(truth, axis=(0, 1, 2, 3))
    truth_std = np.maximum(truth_std, 1e-3)

    def summarize(error: np.ndarray, axes: tuple[int, ...]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        mae = np.nanmean(np.abs(error), axis=axes)
        rmse = np.sqrt(np.nanmean(np.square(error), axis=axes))
        bias = np.nanmean(error, axis=axes)
        return mae, rmse, bias

    # Overall, all leads: (variable, model) and (variable,)
    raw_err = raw - truth[..., None]
    bc_err = bc - truth[..., None]
    blend_err = blend - truth
    raw_mae, raw_rmse, raw_bias = summarize(raw_err, (0, 1, 2, 3))
    bc_mae, bc_rmse, bc_bias = summarize(bc_err, (0, 1, 2, 3))
    blend_mae, blend_rmse, blend_bias = summarize(blend_err, (0, 1, 2, 3))

    # By lead: (lead, variable, model)
    raw_mae_lead, _, _ = summarize(raw_err, (0, 2, 3))
    bc_mae_lead, _, _ = summarize(bc_err, (0, 2, 3))
    blend_mae_lead, _, _ = summarize(blend_err, (0, 2, 3))

    by_variable: dict[str, dict] = {}
    nmae_rows: dict[str, float] = {model: 0.0 for model in cube.models}
    nmae_rows["BLEND"] = 0.0
    n_var = len(cube.variables)

    for var_i, variable in enumerate(cube.variables):
        by_model = {}
        for model_i, model in enumerate(cube.models):
            by_model[model] = _pack(
                float(raw_mae[var_i, model_i]),
                float(raw_rmse[var_i, model_i]),
                float(raw_bias[var_i, model_i]),
                float(raw_mae[var_i, model_i]),  # deterministic CRPS == MAE
                mae_bc=float(bc_mae[var_i, model_i]),
            )
            nmae_rows[model] += float(bc_mae[var_i, model_i] / truth_std[var_i]) / n_var
        by_model["BLEND"] = _pack(
            float(blend_mae[var_i]),
            float(blend_rmse[var_i]),
            float(blend_bias[var_i]),
            float(blend_mae[var_i]),
        )
        nmae_rows["BLEND"] += float(blend_mae[var_i] / truth_std[var_i]) / n_var

        by_lead = []
        for lead_i, lead in enumerate(cube.leads):
            entry = {"lead_hour": int(lead), "models": {}}
            for model_i, model in enumerate(cube.models):
                entry["models"][model] = {
                    "mae": float(raw_mae_lead[lead_i, var_i, model_i]),
                    "mae_bias_corrected": float(bc_mae_lead[lead_i, var_i, model_i]),
                }
            entry["models"]["BLEND"] = {"mae": float(blend_mae_lead[lead_i, var_i])}
            by_lead.append(entry)

        by_season = []
        for season_i, season in enumerate(cube.seasons):
            season_dates = seasons == season_i
            if not np.any(season_dates):
                continue
            s_raw = raw_err[season_dates]
            s_bc = bc_err[season_dates]
            s_blend = blend_err[season_dates]
            s_raw_mae, _, _ = summarize(s_raw, (0, 1, 2, 3))
            s_bc_mae, _, _ = summarize(s_bc, (0, 1, 2, 3))
            s_blend_mae, _, _ = summarize(s_blend, (0, 1, 2, 3))
            models = {
                model: {
                    "mae": float(s_raw_mae[var_i, model_i]),
                    "mae_bias_corrected": float(s_bc_mae[var_i, model_i]),
                }
                for model_i, model in enumerate(cube.models)
            }
            models["BLEND"] = {"mae": float(s_blend_mae[var_i])}
            by_season.append({"season": season, "models": models})

        model_maes = {m: by_model[m]["mae_bias_corrected"] for m in cube.models}
        best_model = min(model_maes, key=model_maes.get)
        best_mae = model_maes[best_model]
        blend_value = by_model["BLEND"]["mae"]
        improvement = (best_mae - blend_value) / best_mae * 100.0 if best_mae else 0.0
        by_variable[variable] = {
            "by_model": by_model,
            "by_lead": by_lead,
            "by_season": by_season,
            "best_model": best_model,
            "best_model_mae_bias_corrected": best_mae,
            "blend_mae": blend_value,
            "improvement_pct_vs_best_corrected": improvement,
            "truth_std": float(truth_std[var_i]),
        }

    best_overall = min(cube.models, key=lambda m: nmae_rows[m])
    improvement_overall = (nmae_rows[best_overall] - nmae_rows["BLEND"]) / nmae_rows[best_overall] * 100.0

    # Ensemble CRPS of the five bias-corrected members (equal weights), averaged
    # over variables after normalizing by the truth standard deviation.
    members = bc
    term1 = np.nanmean(np.abs(members - truth[..., None]), axis=-1)
    pair = 0.0
    n_model = members.shape[-1]
    for i in range(n_model):
        for j in range(n_model):
            pair = pair + np.abs(members[..., i] - members[..., j])
    crps = term1 - pair / (2.0 * n_model * n_model)
    ensemble_crps = np.nanmean(crps, axis=(0, 1, 2, 3)) / truth_std

    return {
        "region": region,
        "by_variable": by_variable,
        "normalized_mae": nmae_rows,
        "best_model_normalized": best_overall,
        "blend_normalized_mae": nmae_rows["BLEND"],
        "improvement_pct_vs_best_normalized": float(improvement_overall),
        "ensemble_crps_normalized": {variable: float(ensemble_crps[i]) for i, variable in enumerate(cube.variables)},
        "crps_note": (
            "For a single deterministic forecast, CRPS equals MAE. "
            "ensemble_crps_normalized scores the five bias-corrected models as an ensemble, "
            "divided by the standard deviation of the observations."
        ),
        "n_test_dates": int(test.sum()),
    }
