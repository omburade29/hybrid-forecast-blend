"""Hybrid AI–NWP forecast blending package.

Pipeline
--------
data_loader  -> ForecastCube
skill_estimator -> bias and MAE conditioned on season, lead, region
weight_model -> adaptive weights (skill table + gating network)
blender      -> bias-corrected weighted consensus
extremes     -> heavy rain, heat, and high-wind probabilities
"""

from blender.pipeline import build_artifacts

__all__ = ["build_artifacts"]
