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
    permutation_anova,
    welch_anova,
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


def test_welch_anova_returns_nan_for_small_groups() -> None:
    frame = pd.DataFrame(
        {
            "group": ["A", "B", "B", "C", "C"],
            "value": [1.0, 2.0, 3.0, 4.0, 5.0],
        }
    )

    result = welch_anova(frame, "group", "value")

    assert pd.isna(result["statistic"])
    assert pd.isna(result["p_value"])


def test_welch_anova_returns_nan_for_all_constant_groups() -> None:
    frame = pd.DataFrame(
        {
            "group": ["A", "A", "B", "B", "C", "C"],
            "value": [1.0, 1.0, 2.0, 2.0, 3.0, 3.0],
        }
    )

    result = welch_anova(frame, "group", "value")

    assert pd.isna(result["statistic"])
    assert pd.isna(result["p_value"])


def test_permutation_anova_returns_nan_for_small_groups() -> None:
    frame = pd.DataFrame(
        {
            "group": ["A", "B", "B", "C", "C"],
            "value": [1.0, 2.0, 3.0, 4.0, 5.0],
        }
    )

    result = permutation_anova(frame, "group", "value")

    assert pd.isna(result["statistic"])
    assert pd.isna(result["p_value"])


def test_permutation_anova_returns_nan_for_all_constant_groups() -> None:
    frame = pd.DataFrame(
        {
            "group": ["A", "A", "B", "B", "C", "C"],
            "value": [1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
        }
    )

    result = permutation_anova(frame, "group", "value")

    assert pd.isna(result["statistic"])
    assert pd.isna(result["p_value"])


def test_welch_and_permutation_anova_normal_case_stability() -> None:
    frame = pd.DataFrame(
        {
            "group": ["A", "A", "A", "B", "B", "B", "C", "C", "C"],
            "value": [1.0, 2.0, 3.0, 2.0, 3.0, 4.0, 3.0, 4.0, 5.0],
        }
    )

    welch = welch_anova(frame, "group", "value")
    permutation = permutation_anova(frame, "group", "value")

    assert np.isclose(welch["statistic"], 18 / 7)
    assert np.isclose(welch["p_value"], 0.191406, atol=0.000001)
    assert permutation["statistic"] == 3.0
    assert permutation["p_value"] == 0.1409295352323838
