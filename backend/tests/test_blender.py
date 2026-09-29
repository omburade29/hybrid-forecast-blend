"""Core blending tests. The archive is deterministic, so thresholds are stable."""

import numpy as np

from blender.constants import HAZARDS, MODELS
from blender.extremes import extreme_probability
from blender.pipeline import build_artifacts

_ARTIFACTS = None


def artifacts():
    global _ARTIFACTS
    if _ARTIFACTS is None:
        _ARTIFACTS = build_artifacts()
    return _ARTIFACTS


def test_weights_are_a_probability_distribution():
    weights = artifacts().weights
    assert weights.shape[-1] == len(MODELS)
    assert np.all(weights >= -1e-8)
    assert np.allclose(weights.sum(axis=-1), 1.0, atol=1e-5)


def test_blend_beats_every_model_on_normalized_mae():
    score = artifacts().metrics
    blend = score["blend_normalized_mae"]
    for model in MODELS:
        assert blend < score["normalized_mae"][model], model
    assert score["improvement_pct_vs_best_normalized"] > 0


def test_blend_beats_best_corrected_model_on_each_variable():
    # Local specialists can be close; the blend should still win the variable
    # it was weighted for, because member errors are complementary.
    for variable, block in artifacts().metrics["by_variable"].items():
        assert block["improvement_pct_vs_best_corrected"] > 0, variable


def test_held_out_dates_are_not_used_as_the_only_sample():
    cube = artifacts().cube
    assert cube.split.sum() > 0
    assert (cube.split == 0).sum() > cube.split.sum()


def test_extreme_probabilities_are_bounded_and_present():
    art = artifacts()
    day = art.cube.index_of_date(art.cube.latest_init())
    season = int(art.cube.season_index[day])
    peak = 0.0
    for hazard in HAZARDS:
        fields = extreme_probability(art.corrected[day], art.weights[season], art.mae[season], hazard)
        probability = fields["probability"]
        assert probability.min() >= 0.0
        assert probability.max() <= 1.0
        assert fields["confidence"].min() >= 0.0
        peak = max(peak, float(probability.max()))
    assert peak > 0.5


def test_latest_cycle_is_the_demo_date():
    assert artifacts().cube.latest_init() == "2026-09-27"
