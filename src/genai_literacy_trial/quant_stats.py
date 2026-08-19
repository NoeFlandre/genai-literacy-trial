from __future__ import annotations

import math
import warnings
import numpy as np
import pandas as pd
from scipy import stats

from genai_literacy_trial.quant_schema import (
    BootstrapSummary,
    CorrelationResult,
    EffectSizeResult,
    SmallSampleSensitivityResult,
    StatisticalTestResult,
)


def _clean(values: pd.Series | np.ndarray) -> np.ndarray:
    return pd.Series(values).dropna().astype(float).to_numpy()


DEFAULT_SEED = int("2026" + "0615")


def mean_ci_bootstrap(values: pd.Series | np.ndarray, seed: int = DEFAULT_SEED, n_boot: int = 10000) -> BootstrapSummary:
    arr = _clean(values)
    if len(arr) == 0:
        return {"mean": math.nan, "ci_low": math.nan, "ci_high": math.nan, "n": 0}
    rng = np.random.default_rng(seed)
    means = rng.choice(arr, size=(n_boot, len(arr)), replace=True).mean(axis=1)
    return {"mean": float(arr.mean()), "ci_low": float(np.quantile(means, 0.025)), "ci_high": float(np.quantile(means, 0.975)), "n": int(len(arr))}


def group_summary_ci(df: pd.DataFrame, group_col: str, value_col: str) -> pd.DataFrame:
    rows = []
    for group, part in df.groupby(group_col, sort=True):
        stat = mean_ci_bootstrap(part[value_col])
        rows.append(
            {
                **stat,
                "group": group,
                "sd": float(part[value_col].dropna().std(ddof=1)) if part[value_col].dropna().shape[0] > 1 else math.nan,
            }
        )
    return pd.DataFrame(rows)[["group", "n", "mean", "sd", "ci_low", "ci_high"]]


def _welch_groups(df: pd.DataFrame, group_col: str, value_col: str) -> list[np.ndarray]:
    return [group for group in (_clean(part[value_col]) for _, part in df.groupby(group_col, sort=True)) if len(group)]


def _welch_is_degenerate(groups: list[np.ndarray]) -> bool:
    if len(groups) < 2:
        return True
    ns = np.array([len(g) for g in groups], dtype=float)
    if np.any(ns < 2):
        return True
    variances = np.array([g.var(ddof=1) for g in groups])
    return bool(np.all(variances == 0))


def _welch_zero_variance_result(groups: list[np.ndarray]) -> StatisticalTestResult | None:
    variances = np.array([group.var(ddof=1) for group in groups])
    if not np.any(variances == 0):
        return None
    result = stats.f_oneway(*groups)
    return {"statistic": float(result.statistic), "p_value": float(result.pvalue)}


def _welch_statistic(groups: list[np.ndarray]) -> StatisticalTestResult:
    ns = np.array([len(group) for group in groups], dtype=float)
    means = np.array([group.mean() for group in groups])
    variances = np.array([group.var(ddof=1) for group in groups])
    weights = ns / variances
    weighted_mean = np.sum(weights * means) / np.sum(weights)
    k = len(groups)
    numerator = np.sum(weights * (means - weighted_mean) ** 2) / (k - 1)
    correction = 1 + (2 * (k - 2) / (k**2 - 1)) * np.sum((1 / (ns - 1)) * (1 - weights / np.sum(weights)) ** 2)
    statistic = numerator / correction
    df_num = k - 1
    df_den = (k**2 - 1) / (3 * np.sum((1 / (ns - 1)) * (1 - weights / np.sum(weights)) ** 2))
    return {"statistic": float(statistic), "p_value": float(stats.f.sf(statistic, df_num, df_den))}


def welch_anova(df: pd.DataFrame, group_col: str, value_col: str) -> StatisticalTestResult:
    groups = _welch_groups(df, group_col, value_col)
    if _welch_is_degenerate(groups):
        return {"statistic": math.nan, "p_value": math.nan}
    fallback = _welch_zero_variance_result(groups)
    return fallback if fallback is not None else _welch_statistic(groups)


def kruskal_test(df: pd.DataFrame, group_col: str, value_col: str) -> StatisticalTestResult:
    groups = [_clean(g[value_col]) for _, g in df.groupby(group_col, sort=True)]
    groups = [g for g in groups if len(g)]
    if len(groups) < 2:
        return {"statistic": math.nan, "p_value": math.nan}
    res = stats.kruskal(*groups)
    return {"statistic": float(res.statistic), "p_value": float(res.pvalue)}


def _permutation_groups(frame: pd.DataFrame, group_col: str, value_col: str) -> list[np.ndarray]:
    return [group[value_col].to_numpy() for _, group in frame.groupby(group_col)]


def _permutation_is_degenerate(groups: list[np.ndarray]) -> bool:
    return any(len(group) < 2 for group in groups) or all(np.var(group, ddof=0) == 0 for group in groups)


def _permutation_p_value(values: np.ndarray, labels: np.ndarray, observed: float, seed: int, n_perm: int) -> float:
    rng = np.random.default_rng(seed)
    count = 0
    for _ in range(n_perm):
        perm = rng.permutation(values)
        stat = stats.f_oneway(*[perm[labels == label] for label in sorted(set(labels))]).statistic
        count += stat >= observed
    return float((count + 1) / (n_perm + 1))


def permutation_anova(
    df: pd.DataFrame,
    group_col: str,
    value_col: str,
    seed: int = DEFAULT_SEED,
    n_perm: int = 2000,
) -> StatisticalTestResult:
    frame = df[[group_col, value_col]].dropna()
    if frame[group_col].nunique() < 2:
        return {"statistic": math.nan, "p_value": math.nan}
    groups = _permutation_groups(frame, group_col, value_col)
    if _permutation_is_degenerate(groups):
        return {"statistic": math.nan, "p_value": math.nan}
    observed = stats.f_oneway(*groups).statistic
    values = frame[value_col].to_numpy()
    labels = frame[group_col].to_numpy()
    return {"statistic": float(observed), "p_value": _permutation_p_value(values, labels, observed, seed, n_perm)}


def _hedges_g_estimate(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) < 2 or len(b) < 2:
        return math.nan
    pooled = math.sqrt(((len(a) - 1) * a.var(ddof=1) + (len(b) - 1) * b.var(ddof=1)) / (len(a) + len(b) - 2))
    if pooled == 0:
        return 0.0
    d = (a.mean() - b.mean()) / pooled
    correction = 1 - 3 / (4 * (len(a) + len(b)) - 9)
    return float(d * correction)


def _valid_hedges_inputs(a: np.ndarray, b: np.ndarray, estimate: float) -> bool:
    return len(a) >= 2 and len(b) >= 2 and bool(np.isfinite(estimate))


def _bootstrap_hedges_g(a: np.ndarray, b: np.ndarray, seed: int, n_boot: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    boots = [_hedges_g_estimate(rng.choice(a, len(a), True), rng.choice(b, len(b), True)) for _ in range(n_boot)]
    return np.array([value for value in boots if np.isfinite(value)])


def hedges_g(
    x: pd.Series | np.ndarray,
    y: pd.Series | np.ndarray,
    seed: int = DEFAULT_SEED,
    n_boot: int = 10000,
) -> EffectSizeResult:
    a, b = _clean(x), _clean(y)
    estimate = _hedges_g_estimate(a, b)
    if not _valid_hedges_inputs(a, b, estimate):
        return {"estimate": estimate, "ci_low": math.nan, "ci_high": math.nan}
    boots = _bootstrap_hedges_g(a, b, seed, n_boot)
    return {"estimate": estimate, "ci_low": float(np.quantile(boots, 0.025)), "ci_high": float(np.quantile(boots, 0.975))}


def pearson_with_fisher_ci(x: pd.Series | np.ndarray, y: pd.Series | np.ndarray) -> CorrelationResult:
    frame = pd.DataFrame({"x": x, "y": y}).dropna()
    n = len(frame)
    if n < 4:
        return {"correlation": math.nan, "p_value": math.nan, "ci_low": math.nan, "ci_high": math.nan, "n": n}
    r, p = stats.pearsonr(frame["x"], frame["y"])
    r_clip = max(min(float(r), 0.999999), -0.999999)
    z = np.arctanh(r_clip)
    se = 1 / math.sqrt(n - 3)
    return {"correlation": float(r), "p_value": float(p), "ci_low": float(np.tanh(z - 1.96 * se)), "ci_high": float(np.tanh(z + 1.96 * se)), "n": n}


def spearman_with_ci(
    x: pd.Series | np.ndarray,
    y: pd.Series | np.ndarray,
    seed: int = DEFAULT_SEED,
    n_boot: int = 10000,
) -> CorrelationResult:
    frame = pd.DataFrame({"x": x, "y": y}).dropna()
    if len(frame) < 3:
        return {"correlation": math.nan, "p_value": math.nan, "ci_low": math.nan, "ci_high": math.nan, "n": len(frame)}
    if np.nanvar(frame["x"], ddof=0) == 0 or np.nanvar(frame["y"], ddof=0) == 0:
        return {"correlation": math.nan, "p_value": math.nan, "ci_low": math.nan, "ci_high": math.nan, "n": len(frame)}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=stats.ConstantInputWarning)
        r, p = stats.spearmanr(frame["x"], frame["y"])
    vals = _spearman_bootstrap(frame, seed=seed, n_boot=n_boot)
    if len(vals) == 0:
        return {"correlation": float(r), "p_value": float(p), "ci_low": math.nan, "ci_high": math.nan, "n": len(frame)}
    return {"correlation": float(r), "p_value": float(p), "ci_low": float(np.quantile(vals, 0.025)), "ci_high": float(np.quantile(vals, 0.975)), "n": len(frame)}


def _spearman_bootstrap(frame: pd.DataFrame, *, seed: int, n_boot: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n_boot):
        sample = frame.iloc[rng.choice(len(frame), len(frame), True)]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=stats.ConstantInputWarning)
            vals.append(stats.spearmanr(sample["x"], sample["y"]).statistic)
    return np.array([value for value in vals if np.isfinite(value)])


def benjamini_hochberg(p_values: list[float] | pd.Series) -> list[float]:
    p = np.array([1.0 if pd.isna(v) else float(v) for v in p_values])
    order = np.argsort(p)
    ranked = p[order]
    m = len(p)
    adj_sorted = np.minimum.accumulate((ranked * m / np.arange(1, m + 1))[::-1])[::-1]
    adj_sorted = np.clip(adj_sorted, 0, 1)
    out = np.empty_like(adj_sorted)
    out[order] = adj_sorted
    return [float(x) for x in out]


def cronbach_alpha(items_df: pd.DataFrame) -> float:
    df = items_df.dropna()
    k = df.shape[1]
    if k < 2 or df.empty:
        return math.nan
    item_var = df.var(axis=0, ddof=1).sum()
    total_var = df.sum(axis=1).var(ddof=1)
    if total_var == 0:
        return math.nan
    return float(k / (k - 1) * (1 - item_var / total_var))


def standardize_series(series: pd.Series) -> pd.Series:
    s = series.astype(float)
    sd = s.std(ddof=1)
    if sd == 0 or pd.isna(sd):
        return s * 0
    return (s - s.mean()) / sd


def small_sample_sensitivity(n_a: int = 13, n_b: int = 13, n_c: int = 19) -> SmallSampleSensitivityResult:
    z = stats.norm.ppf(0.975) + stats.norm.ppf(0.80)
    d_ab = z * math.sqrt(1 / n_a + 1 / n_b)
    pooled = n_a + n_b
    d_c_pool = z * math.sqrt(1 / n_c + 1 / pooled)
    n = n_a + n_b + n_c
    r = math.tanh(z / math.sqrt(n - 3))
    return {
        "detectable_d_a_vs_b_80_power": float(d_ab),
        "detectable_d_c_vs_pooled_ab_80_power": float(d_c_pool),
        "detectable_r_n45_80_power": float(r),
        "interpretation": "Powered only for relatively large effects; do not claim sample-size adequacy.",
    }
