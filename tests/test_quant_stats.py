from __future__ import annotations

import inspect
import warnings
from typing import Literal

import numpy as np
import pandas as pd
import pytest
from scipy import stats

import genai_literacy_trial.quant_stats as quant_stats
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


def test_clean_converts_numeric_strings_to_float_values() -> None:
    cleaned = quant_stats._clean(pd.Series(["1", "2", None]))

    assert cleaned.dtype == np.dtype(float)
    np.testing.assert_array_equal(cleaned, [1.0, 2.0])


def test_mean_bootstrap_uses_the_documented_default_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[int, int]] = []

    class FakeRng:
        def choice(self, _values: np.ndarray, *, size: tuple[int, int], replace: bool) -> np.ndarray:
            calls.append(size)
            assert replace is True
            return np.ones(size)

    monkeypatch.setattr(quant_stats.np.random, "default_rng", lambda _seed: FakeRng())

    mean_ci_bootstrap(pd.Series([1.0, 2.0, 3.0]))

    assert calls == [(10000, 3)]


def test_mean_bootstrap_coerces_numeric_string_inputs() -> None:
    result = mean_ci_bootstrap(pd.Series(["1", "2", "3"]), seed=123, n_boot=5)

    assert result["mean"] == 2.0
    assert result["n"] == 3


def test_bootstrap_public_defaults_are_stable() -> None:
    assert inspect.signature(mean_ci_bootstrap).parameters["n_boot"].default == 10000
    assert inspect.signature(hedges_g).parameters["n_boot"].default == 10000
    assert inspect.signature(spearman_with_ci).parameters["n_boot"].default == 10000


def test_hedges_bootstrap_forwards_seed_and_default_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    seeds: list[int | None] = []
    choice_calls = 0
    original_default_rng = quant_stats.np.random.default_rng

    def recording_default_rng(seed: int | None):
        seeds.append(seed)
        return original_default_rng(seed)

    class FakeRng:
        def choice(self, values: np.ndarray, size: int, replace: bool) -> np.ndarray:
            nonlocal choice_calls
            choice_calls += 1
            assert replace is True
            return np.resize(values, size)

    monkeypatch.setattr(quant_stats.np.random, "default_rng", recording_default_rng)
    hedges_g(pd.Series([1.0, 2.0]), pd.Series([2.0, 3.0]), seed=17, n_boot=2)
    assert seeds == [17]

    monkeypatch.setattr(quant_stats.np.random, "default_rng", lambda _seed: FakeRng())
    hedges_g(pd.Series([1.0, 2.0]), pd.Series([2.0, 3.0]))
    assert choice_calls == 20000


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


def test_group_summary_ci_reports_undefined_sd_for_singleton_groups() -> None:
    result = group_summary_ci(
        pd.DataFrame({"group": ["A", "B", "B"], "value": [1.0, 2.0, 4.0]}),
        "group",
        "value",
    )

    singleton = result.loc[result["group"] == "A"].iloc[0]
    repeated = result.loc[result["group"] == "B"].iloc[0]
    assert singleton["n"] == 1
    assert pd.isna(singleton["sd"])
    assert repeated["n"] == 2
    assert repeated["sd"] == np.sqrt(2)


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
    np.testing.assert_allclose(standardize_series(pd.Series(["1", "2", "3"])), [-1.0, 0.0, 1.0])


def test_statistical_boundaries_keep_invalid_inputs_invalid() -> None:
    one_element_welch = quant_stats._welch_is_degenerate([np.array([1.0]), np.array([2.0, 3.0])])
    one_element_permutation = quant_stats._permutation_is_degenerate([np.array([1.0]), np.array([2.0, 3.0])])
    one_element_effect = hedges_g(pd.Series([1.0]), pd.Series([2.0, 3.0]), seed=123, n_boot=100)

    assert one_element_welch is True
    assert one_element_permutation is True
    assert pd.isna(one_element_effect["estimate"])
    assert pd.isna(one_element_effect["ci_low"])
    assert pd.isna(one_element_effect["ci_high"])
    assert quant_stats._valid_hedges_inputs(np.array([1.0]), np.array([2.0, 3.0]), 0.5) is False
    assert quant_stats._valid_hedges_inputs(np.array([1.0, 2.0]), np.array([3.0, 4.0]), 0.5) is True
    assert pd.isna(quant_stats._hedges_g_estimate(np.array([1.0]), np.array([2.0, 3.0])))


def test_hedges_g_estimate_short_circuits_before_invalid_singleton_math(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(quant_stats.math, "sqrt", lambda *_args: pytest.fail("unexpected pooled standard deviation"))

    assert pd.isna(quant_stats._hedges_g_estimate(np.array([1.0]), np.array([2.0, 3.0])))


def test_cronbach_alpha_uses_the_standard_two_item_formula() -> None:
    assert cronbach_alpha(pd.DataFrame({"a": [1.0, 2.0, 3.0], "b": [1.0, 2.0, 3.0]})) == 1.0


def test_pearson_negative_boundary_keeps_confidence_interval_negative() -> None:
    result = pearson_with_fisher_ci(pd.Series([1, 2, 3, 4, 5]), pd.Series([5, 4, 3, 2, 1]))
    positive = pearson_with_fisher_ci(pd.Series([1, 2, 3, 4, 5]), pd.Series([1, 2, 3, 4, 5]))

    assert result["correlation"] == -1.0
    assert np.isfinite(result["ci_low"])
    assert np.isfinite(result["ci_high"])
    assert result["ci_high"] < 0
    assert np.isclose(result["ci_low"], -positive["ci_high"])
    assert np.isclose(result["ci_high"], -positive["ci_low"])
    assert np.isclose(positive["ci_low"], 0.9999840117977937)
    assert np.isclose(positive["ci_high"], 0.9999999374543203)


def test_spearman_empty_bootstrap_preserves_sample_size_field(monkeypatch: pytest.MonkeyPatch) -> None:
    original = quant_stats._spearman_bootstrap
    monkeypatch.setattr(quant_stats, "_spearman_bootstrap", lambda *_args, **_kwargs: np.array([]))

    result = spearman_with_ci(pd.Series([1.0, 2.0, 3.0]), pd.Series([3.0, 2.0, 1.0]), seed=11, n_boot=5)

    assert result["n"] == 3
    assert result["correlation"] == -1.0
    assert pd.isna(result["ci_low"])
    assert pd.isna(result["ci_high"])
    monkeypatch.setattr(quant_stats, "_spearman_bootstrap", original)


def test_benjamini_hochberg_clips_out_of_range_values() -> None:
    assert benjamini_hochberg([-0.2, 0.4, 1.5]) == [0.0, 0.6000000000000001, 1.0]


def test_cronbach_alpha_handles_unit_total_variance_without_collapsing() -> None:
    result = cronbach_alpha(pd.DataFrame({"a": [0.0, 1.0, 2.0], "b": [0.0, 0.0, 0.0]}))

    assert result == 0.0


def test_cronbach_alpha_matches_the_standard_formula_for_nonperfect_items() -> None:
    result = cronbach_alpha(pd.DataFrame({"a": [1.0, 2.0, 3.0], "b": [1.0, 2.0, 4.0]}))

    assert np.isclose(result, 0.9473684210526316)
    three_items = cronbach_alpha(
        pd.DataFrame(
            {
                "a": [1.0, 2.0, 3.0, 4.0],
                "b": [1.0, 2.0, 4.0, 4.0],
                "c": [2.0, 2.0, 3.0, 5.0],
            }
        )
    )
    assert np.isclose(three_items, 0.9538461538461538)


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


def test_standardize_series_returns_float_values_for_numeric_strings() -> None:
    standardized = standardize_series(pd.Series(["1", "2", "3"]))

    assert standardized.dtype == np.dtype(float)
    np.testing.assert_allclose(standardized, [-1.0, 0.0, 1.0])


def test_benjamini_hochberg_preserves_original_order_and_handles_missing_p_values() -> None:
    adjusted = benjamini_hochberg(pd.Series([0.04, np.nan, 0.01, 0.03]))

    assert np.allclose(adjusted, [0.05333333333333334, 1.0, 0.04, 0.05333333333333334])
    assert benjamini_hochberg([np.nan]) == [1.0]


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


def test_spearman_uses_a_narrow_constant_input_warning_filter(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[object] = []

    def recording_simplefilter(
        _action: Literal["default", "error", "ignore", "always", "all", "module", "once"],
        category: type[Warning] | tuple[type[Warning], ...] = Warning,
    ) -> None:
        calls.append(category)

    monkeypatch.setattr(quant_stats.warnings, "simplefilter", recording_simplefilter)

    spearman_with_ci(pd.Series([1.0, 1.0, 2.0]), pd.Series([1.0, 2.0, 3.0]), n_boot=2)

    assert sum(category is stats.ConstantInputWarning for category in calls) == 3


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


def test_spearman_constant_input_short_circuits_before_correlation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(quant_stats.stats, "spearmanr", lambda *_args, **_kwargs: pytest.fail("unexpected correlation call"))

    result = spearman_with_ci(pd.Series([1.0, 1.0, 1.0]), pd.Series([1.0, 2.0, 3.0]))

    assert pd.isna(result["correlation"])


def test_spearman_constant_y_short_circuits_before_correlation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(quant_stats.stats, "spearmanr", lambda *_args, **_kwargs: pytest.fail("unexpected correlation call"))

    result = spearman_with_ci(pd.Series([1.0, 2.0, 3.0]), pd.Series([1.0, 1.0, 1.0]))

    assert pd.isna(result["correlation"])


def test_spearman_keeps_nonconstant_unit_variance_inputs() -> None:
    result = spearman_with_ci(pd.Series([0.0, 1.0, 2.0]), pd.Series([0.0, 1.0, 2.0]), n_boot=5)

    assert result["correlation"] == 1.0
    assert result["n"] == 3


def test_spearman_does_not_treat_population_variance_one_as_constant() -> None:
    values = pd.Series([-1.0, -1.0, 1.0, 1.0])

    result = spearman_with_ci(values, values, n_boot=5)

    assert result["correlation"] == 1.0
    assert result["n"] == 4


def test_spearman_uses_the_default_seed_and_bootstrap_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[int, int]] = []

    def fake_bootstrap(_frame: pd.DataFrame, *, seed: int, n_boot: int) -> np.ndarray:
        calls.append((seed, n_boot))
        return np.array([0.5])

    monkeypatch.setattr(quant_stats, "_spearman_bootstrap", fake_bootstrap)

    spearman_with_ci(pd.Series([1.0, 2.0, 3.0]), pd.Series([3.0, 2.0, 1.0]))

    assert calls == [(20260615, 10000)]


def test_spearman_forwards_the_requested_seed_to_bootstrap(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[int | None, int]] = []

    def fake_bootstrap(_frame: pd.DataFrame, *, seed: int, n_boot: int) -> np.ndarray:
        calls.append((seed, n_boot))
        return np.array([0.5])

    monkeypatch.setattr(quant_stats, "_spearman_bootstrap", fake_bootstrap)

    spearman_with_ci(pd.Series([1.0, 2.0, 3.0]), pd.Series([3.0, 2.0, 1.0]), seed=17, n_boot=4)

    assert calls == [(17, 4)]


def test_spearman_bootstrap_preserves_seed_and_replacement_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[int, int, int | None, bool | None]] = []

    class FakeRng:
        def __init__(self, seed: int | None):
            self.seed = seed

        def choice(self, length: int, size: int, replace: bool | None):
            calls.append((length, size, self.seed, replace))
            return np.arange(size)

    monkeypatch.setattr(quant_stats.np.random, "default_rng", lambda seed: FakeRng(seed))

    result = quant_stats._spearman_bootstrap(
        pd.DataFrame({"x": [1.0, 2.0], "y": [1.0, 2.0]}), seed=11, n_boot=2
    )

    assert np.allclose(result, [1.0, 1.0])
    assert calls == [(2, 2, 11, True), (2, 2, 11, True)]


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
