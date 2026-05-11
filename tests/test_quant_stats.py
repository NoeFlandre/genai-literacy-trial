from __future__ import annotations

import numpy as np
import pandas as pd

from genai_literacy_trial.quant_stats import (
    benjamini_hochberg,
    cronbach_alpha,
    hedges_g,
    mean_ci_bootstrap,
    pearson_with_fisher_ci,
    small_sample_sensitivity,
)


def test_bootstrap_and_effect_size_helpers_are_deterministic() -> None:
    values = pd.Series([1, 2, 3, 4, 5])

    first = mean_ci_bootstrap(values, seed=123, n_boot=500)
    second = mean_ci_bootstrap(values, seed=123, n_boot=500)
    effect = hedges_g(pd.Series([3, 4, 5]), pd.Series([1, 2, 3]), n_boot=500)

    assert first == second
    assert first["mean"] == 3
    assert effect["estimate"] > 0
    assert effect["ci_low"] < effect["estimate"] < effect["ci_high"]


def test_correlation_fdr_reliability_and_sensitivity_outputs() -> None:
    corr = pearson_with_fisher_ci(pd.Series([1, 2, 3, 4, 5]), pd.Series([2, 4, 6, 8, 10]))
    adjusted = benjamini_hochberg([0.01, 0.04, 0.03])
    alpha = cronbach_alpha(pd.DataFrame({"a": [1, 2, 3, 4], "b": [1, 2, 3, 4], "c": [2, 3, 4, 5]}))
    sensitivity = small_sample_sensitivity()

    assert corr["correlation"] > 0.99
    assert np.isfinite(corr["ci_low"])
    assert adjusted == sorted(adjusted)
    assert alpha > 0.9
    assert sensitivity["detectable_d_a_vs_b_80_power"] > 1
    assert sensitivity["detectable_r_n45_80_power"] > 0.3

