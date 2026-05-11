from __future__ import annotations

import math
import numpy as np
import pandas as pd
from scipy import stats


def _clean(values: pd.Series | np.ndarray) -> np.ndarray:
    return pd.Series(values).dropna().astype(float).to_numpy()


DEFAULT_SEED = int("2026" + "0615")


def mean_ci_bootstrap(values: pd.Series | np.ndarray, seed: int = DEFAULT_SEED, n_boot: int = 10000) -> dict[str, float]:
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
        stat["group"] = group
        stat["sd"] = float(part[value_col].dropna().std(ddof=1)) if part[value_col].dropna().shape[0] > 1 else math.nan
        rows.append(stat)
    return pd.DataFrame(rows)[["group", "n", "mean", "sd", "ci_low", "ci_high"]]


def welch_anova(df: pd.DataFrame, group_col: str, value_col: str) -> dict[str, float]:
    groups = [_clean(g[value_col]) for _, g in df.groupby(group_col, sort=True)]
    groups = [g for g in groups if len(g)]
    if len(groups) < 2:
        return {"statistic": math.nan, "p_value": math.nan}
    means = np.array([g.mean() for g in groups])
    variances = np.array([g.var(ddof=1) for g in groups])
    ns = np.array([len(g) for g in groups], dtype=float)
    if np.any(ns < 2) or np.any(variances == 0):
        res = stats.f_oneway(*groups)
        return {"statistic": float(res.statistic), "p_value": float(res.pvalue)}
    weights = ns / variances
    weighted_mean = np.sum(weights * means) / np.sum(weights)
    k = len(groups)
    numerator = np.sum(weights * (means - weighted_mean) ** 2) / (k - 1)
    correction = 1 + (2 * (k - 2) / (k**2 - 1)) * np.sum((1 / (ns - 1)) * (1 - weights / np.sum(weights)) ** 2)
    statistic = numerator / correction
    df_num = k - 1
    df_den = (k**2 - 1) / (3 * np.sum((1 / (ns - 1)) * (1 - weights / np.sum(weights)) ** 2))
    return {"statistic": float(statistic), "p_value": float(stats.f.sf(statistic, df_num, df_den))}


def kruskal_test(df: pd.DataFrame, group_col: str, value_col: str) -> dict[str, float]:
    groups = [_clean(g[value_col]) for _, g in df.groupby(group_col, sort=True)]
    groups = [g for g in groups if len(g)]
    if len(groups) < 2:
        return {"statistic": math.nan, "p_value": math.nan}
    res = stats.kruskal(*groups)
    return {"statistic": float(res.statistic), "p_value": float(res.pvalue)}


def permutation_anova(df: pd.DataFrame, group_col: str, value_col: str, seed: int = DEFAULT_SEED, n_perm: int = 2000) -> dict[str, float]:
    frame = df[[group_col, value_col]].dropna()
    if frame[group_col].nunique() < 2:
        return {"statistic": math.nan, "p_value": math.nan}
    observed = stats.f_oneway(*[g[value_col].to_numpy() for _, g in frame.groupby(group_col)]).statistic
    rng = np.random.default_rng(seed)
    values = frame[value_col].to_numpy()
    labels = frame[group_col].to_numpy()
    count = 0
    for _ in range(n_perm):
        perm = rng.permutation(values)
        stat = stats.f_oneway(*[perm[labels == label] for label in sorted(set(labels))]).statistic
        count += stat >= observed
    return {"statistic": float(observed), "p_value": float((count + 1) / (n_perm + 1))}


def hedges_g(x: pd.Series | np.ndarray, y: pd.Series | np.ndarray, seed: int = DEFAULT_SEED, n_boot: int = 10000) -> dict[str, float]:
    a, b = _clean(x), _clean(y)
    def calc(u: np.ndarray, v: np.ndarray) -> float:
        if len(u) < 2 or len(v) < 2:
            return math.nan
        pooled = math.sqrt(((len(u) - 1) * u.var(ddof=1) + (len(v) - 1) * v.var(ddof=1)) / (len(u) + len(v) - 2))
        if pooled == 0:
            return 0.0
        d = (u.mean() - v.mean()) / pooled
        correction = 1 - 3 / (4 * (len(u) + len(v)) - 9)
        return float(d * correction)
    estimate = calc(a, b)
    if len(a) < 2 or len(b) < 2 or not np.isfinite(estimate):
        return {"estimate": estimate, "ci_low": math.nan, "ci_high": math.nan}
    rng = np.random.default_rng(seed)
    boots = [calc(rng.choice(a, len(a), True), rng.choice(b, len(b), True)) for _ in range(n_boot)]
    boots = np.array([v for v in boots if np.isfinite(v)])
    return {"estimate": estimate, "ci_low": float(np.quantile(boots, 0.025)), "ci_high": float(np.quantile(boots, 0.975))}


def pearson_with_fisher_ci(x: pd.Series | np.ndarray, y: pd.Series | np.ndarray) -> dict[str, float]:
    frame = pd.DataFrame({"x": x, "y": y}).dropna()
    n = len(frame)
    if n < 4:
        return {"correlation": math.nan, "p_value": math.nan, "ci_low": math.nan, "ci_high": math.nan, "n": n}
    r, p = stats.pearsonr(frame["x"], frame["y"])
    r_clip = max(min(float(r), 0.999999), -0.999999)
    z = np.arctanh(r_clip)
    se = 1 / math.sqrt(n - 3)
    return {"correlation": float(r), "p_value": float(p), "ci_low": float(np.tanh(z - 1.96 * se)), "ci_high": float(np.tanh(z + 1.96 * se)), "n": n}


def spearman_with_ci(x: pd.Series | np.ndarray, y: pd.Series | np.ndarray, seed: int = DEFAULT_SEED, n_boot: int = 10000) -> dict[str, float]:
    frame = pd.DataFrame({"x": x, "y": y}).dropna()
    if len(frame) < 3:
        return {"correlation": math.nan, "p_value": math.nan, "ci_low": math.nan, "ci_high": math.nan, "n": len(frame)}
    r, p = stats.spearmanr(frame["x"], frame["y"])
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n_boot):
        sample = frame.iloc[rng.choice(len(frame), len(frame), True)]
        vals.append(stats.spearmanr(sample["x"], sample["y"]).statistic)
    vals = np.array([v for v in vals if np.isfinite(v)])
    return {"correlation": float(r), "p_value": float(p), "ci_low": float(np.quantile(vals, 0.025)), "ci_high": float(np.quantile(vals, 0.975)), "n": len(frame)}


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


def small_sample_sensitivity(n_a: int = 13, n_b: int = 13, n_c: int = 19) -> dict[str, float | str]:
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
