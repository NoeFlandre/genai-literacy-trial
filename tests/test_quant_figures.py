from __future__ import annotations

from pathlib import Path

import pandas as pd

from genai_literacy_trial.quant_figures import (
    plot_calibration_forest,
    plot_learning_outcome,
    plot_prompt_quality_trajectory,
)


def test_quant_figures_write_pdf_and_png_without_raw_ids(tmp_path: Path) -> None:
    trajectory = pd.DataFrame(
        {"group": ["A", "A", "B"], "assignment": [1, 2, 1], "mean": [2.0, 3.0, 4.0], "ci_low": [1.8, 2.8, 3.8], "ci_high": [2.2, 3.2, 4.2]}
    )
    learning = pd.DataFrame({"mean_prompt_score": [2.0, 3.0, 4.0], "predicted_final_points": [2.5, 3.0, 3.5], "ci_low": [2.3, 2.8, 3.3], "ci_high": [2.7, 3.2, 3.7]})
    calibration = pd.DataFrame({"dimension": ["trust", "usefulness"], "std_beta": [0.2, -0.1], "std_ci_low": [0.0, -0.3], "std_ci_high": [0.4, 0.1], "fdr_p_value": [0.04, 0.5]})

    outputs = []
    outputs += plot_prompt_quality_trajectory(trajectory, tmp_path)
    outputs += plot_learning_outcome(learning, tmp_path)
    outputs += plot_calibration_forest(calibration, tmp_path)

    assert len(outputs) == 6
    for path in outputs:
        assert path.exists()
        assert path.stat().st_size > 0
        assert "p01" not in path.name
