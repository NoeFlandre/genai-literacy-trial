from __future__ import annotations

import inspect
import warnings

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from genai_literacy_trial.quant_stats import (
    benjamini_hochberg,
    cronbach_alpha,
    group_summary_ci,
    hedges_g,
    kruskal_test,
    mean_ci_bootstrap,
    pearson_with_fisher_ci,
    small_sample_sensitivity,
    permutation_anova,
    spearman_with_ci,
    standardize_series,
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


def test_statistical_output_contracts_match_small_golden_fixtures() -> None:
    mean = mean_ci_bootstrap(pd.Series([1, 2, 3, 4, 5]), seed=123, n_boot=500)
    effect = hedges_g(pd.Series([3, 4, 5]), pd.Series([1, 2, 3]), seed=123, n_boot=500)
    correlation = pearson_with_fisher_ci(pd.Series([1, 2, 3, 4, 5]), pd.Series([2, 4, 6, 8, 10]))
    sensitivity = small_sample_sensitivity()

    assert mean == {"mean": 3.0, "ci_low": 1.6, "ci_high": 4.2, "n": 5}
    assert effect["estimate"] == 1.6
    assert np.isclose(effect["ci_low"], 0.8763560920082659)
    assert np.isclose(effect["ci_high"], 5.225578117937447)
    assert correlation["n"] == 5
    assert correlation["correlation"] == 1.0
    assert np.isclose(correlation["ci_low"], 0.9999840117977937)
    assert np.isclose(correlation["ci_high"], 0.9999999374543203)
    assert set(sensitivity) == {
        "detectable_d_a_vs_b_80_power",
        "detectable_d_c_vs_pooled_ab_80_power",
        "detectable_r_n45_80_power",
        "interpretation",
    }
    assert np.isclose(sensitivity["detectable_d_a_vs_b_80_power"], 1.0988721304731635)
    assert np.isclose(sensitivity["detectable_d_c_vs_pooled_ab_80_power"], 0.8455642631813689)
    assert np.isclose(sensitivity["detectable_r_n45_80_power"], 0.40723664075787896)
    assert sensitivity["interpretation"] == "Powered only for relatively large effects; do not claim sample-size adequacy."


def test_bootstrap_public_defaults_are_stable() -> None:
    assert inspect.signature(mean_ci_bootstrap).parameters["n_boot"].default == 10000
    assert inspect.signature(hedges_g).parameters["n_boot"].default == 10000
    assert inspect.signature(spearman_with_ci).parameters["n_boot"].default == 10000


def test_group_summary_ci_preserves_sorted_groups_and_sample_statistics() -> None:
    result = group_summary_ci(
        pd.DataFrame({"group": ["B", "A", "B", "A"], "value": [3.0, 1.0, 5.0, 2.0]}),
        "group",
        "value",
    )

    expected = pd.DataFrame(
        {
            "group": ["A", "B"],
            "n": [2, 2],
            "mean": [1.5, 4.0],
            "sd": [0.7071067811865476, 1.4142135623730951],
            "ci_low": [1.0, 3.0],
            "ci_high": [2.0, 5.0],
        }
    )
    pd.testing.assert_frame_equal(result, expected)


def test_two_group_and_boundary_statistical_cases_are_not_collapsed() -> None:
    frame = pd.DataFrame({"group": ["A", "A", "B", "B"], "value": [1.0, 2.0, 4.0, 5.0]})
    kruskal = kruskal_test(frame, "group", "value")
    permutation = permutation_anova(frame, "group", "value", seed=123, n_perm=200)
    pearson_at_boundary = pearson_with_fisher_ci(pd.Series([1, 2, 3, 4]), pd.Series([4, 3, 2, 1]))

    assert np.isclose(kruskal["statistic"], 2.4)
    assert np.isclose(kruskal["p_value"], 0.12133525035848211)
    assert np.isclose(permutation["statistic"], 18.0)
    assert np.isclose(permutation["p_value"], 0.30845771144278605)
    assert pearson_at_boundary["n"] == 4
    assert np.isfinite(pearson_at_boundary["ci_low"])
    assert np.isfinite(pearson_at_boundary["ci_high"])


def test_correlation_and_reliability_edge_cases_keep_their_contracts() -> None:
    short = spearman_with_ci(pd.Series([1.0, 2.0]), pd.Series([2.0, 1.0]))
    constant_y = spearman_with_ci(pd.Series([1.0, 2.0, 3.0]), pd.Series([1.0, 1.0, 1.0]))
    constant_items = cronbach_alpha(pd.DataFrame({"a": [1.0, 1.0], "b": [1.0, 1.0]}))
    one_item = cronbach_alpha(pd.DataFrame({"a": [1.0, 2.0]}))
    standardized = standardize_series(pd.Series([1.0, 2.0, 3.0]))
    constant_standardized = standardize_series(pd.Series([2.0, 2.0]))

    assert short["n"] == 2
    assert all(pd.isna(short[key]) for key in ("correlation", "p_value", "ci_low", "ci_high"))
    assert pd.isna(constant_y["correlation"])
    assert pd.isna(constant_y["p_value"])
    assert pd.isna(constant_items)
    assert pd.isna(one_item)
    np.testing.assert_allclose(standardized, [-1.0, 0.0, 1.0])
    np.testing.assert_allclose(constant_standardized, [0.0, 0.0])


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


def test_benjamini_hochberg_preserves_original_order_and_handles_missing_p_values() -> None:
    adjusted = benjamini_hochberg(pd.Series([0.04, np.nan, 0.01, 0.03]))

    assert np.allclose(adjusted, [0.05333333333333334, 1.0, 0.04, 0.05333333333333334])


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


def test_spearman_with_ci_normal_case_is_finite_and_deterministic() -> None:
    x = pd.Series([1, 2, 3, 4, 5, 6])
    y = pd.Series([1, 2, 3, 4, 5, 6])

    first = spearman_with_ci(x, y, seed=123, n_boot=200)
    second = spearman_with_ci(x, y, seed=123, n_boot=200)

    assert first["n"] == len(x)
    assert np.isfinite(first["correlation"])
    assert np.isfinite(first["p_value"])
    assert np.isfinite(first["ci_low"])
    assert np.isfinite(first["ci_high"])
    assert first == second


def test_spearman_with_ci_tie_heavy_data_suppresses_constantinputwarning() -> None:
    x = pd.Series([1, 1, 1, 2, 2, 2])
    y = pd.Series([1, 1, 2, 2, 2, 1])

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = spearman_with_ci(x, y, seed=123, n_boot=500)

    assert result["n"] == 6
    assert np.isfinite(result["correlation"])
    assert np.isfinite(result["p_value"])
    assert np.isfinite(result["ci_low"])
    assert np.isfinite(result["ci_high"])
    assert not any(issubclass(w.category, stats.ConstantInputWarning) for w in caught)


def test_spearman_with_ci_constant_input_returns_nan_without_warning() -> None:
    x = pd.Series([1, 1, 1, 1, 1, 1])
    y = pd.Series([1, 2, 3, 4, 5, 6])

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = spearman_with_ci(x, y)

    assert result["n"] == 6
    assert pd.isna(result["correlation"])
    assert pd.isna(result["p_value"])
    assert pd.isna(result["ci_low"])
    assert pd.isna(result["ci_high"])
    assert not any(issubclass(w.category, stats.ConstantInputWarning) for w in caught)


def test_spearman_with_ci_handles_empty_finite_bootstrap(monkeypatch: pytest.MonkeyPatch) -> None:
    import genai_literacy_trial.quant_stats as quant_stats

    class _FakeResult:
        def __init__(self, statistic: float, pvalue: float = 1.0):
            self.statistic = statistic
            self.pvalue = pvalue

        def __iter__(self):
            return iter((self.statistic, self.pvalue))

    original = quant_stats.stats.spearmanr
    calls = {"n": 0}

    def always_nan_after_first(_x: pd.Series, _y: pd.Series):
        calls["n"] += 1
        if calls["n"] == 1:
            return original(_x, _y)
        return _FakeResult(float("nan"), float("nan"))

    monkeypatch.setattr(quant_stats.stats, "spearmanr", always_nan_after_first)

    result = quant_stats.spearman_with_ci(
        pd.Series([1.0, 2.0, 3.0]),
        pd.Series([3.0, 2.0, 1.0]),
        seed=11,
        n_boot=5,
    )

    assert np.isfinite(result["correlation"])
    assert np.isfinite(result["p_value"])
    assert pd.isna(result["ci_low"])
    assert pd.isna(result["ci_high"])
