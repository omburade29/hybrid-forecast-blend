"""Train the adaptive weight model and print the held-out scorecard.

Usage (from the backend directory):

    python scripts/train_weights.py

The script writes `data/artifacts.npz` (weights, bias, MAE, gating coefficients).
The API retrains on startup from the same deterministic archive, so this file
is an inspection and hand-off artifact rather than something the server requires.

Swap `build_artifacts` inputs by setting DATA_SOURCE=directory — see
`blender/data_loader.py`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from blender.pipeline import build_artifacts  # noqa: E402


def main() -> None:
    artifacts = build_artifacts()
    out = ROOT / "data"
    out.mkdir(parents=True, exist_ok=True)
    artifacts.weight_model.save(out / "gating_weights.npz")
    import numpy as np

    np.savez_compressed(
        out / "artifacts.npz",
        bias=artifacts.bias,
        mae=artifacts.mae,
        rmse=artifacts.rmse,
        weights=artifacts.weights,
        lats=artifacts.cube.lats,
        lons=artifacts.cube.lons,
    )
    score = artifacts.metrics
    card = {
        "trained_at": artifacts.trained_at,
        "normalized_mae": {key: round(val, 4) for key, val in score["normalized_mae"].items()},
        "best_model": score["best_model_normalized"],
        "improvement_pct_vs_best_normalized": round(score["improvement_pct_vs_best_normalized"], 2),
        "per_variable_improvement_pct": {
            variable: round(block["improvement_pct_vs_best_corrected"], 2)
            for variable, block in score["by_variable"].items()
        },
    }
    (out / "scorecard.json").write_text(json.dumps(card, indent=2), encoding="utf-8")
    print(json.dumps(card, indent=2))
    print(f"Wrote {out / 'artifacts.npz'}")


if __name__ == "__main__":
    main()
