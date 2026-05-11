from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.formula.api as smf

from genai_literacy_trial.quant_stats import (
    benjamini_hochberg,
    group_summary_ci,
    hedges_g,
    kruskal_test,
    mean_ci_bootstrap,
    pearson_with_fisher_ci,
    permutation_anova,
    spearman_with_ci,
    standardize_series,
    welch_anova,
)


@dataclass
class ModelSummary:
    formula: str
    n_observations: int
    n_participants: int
    method: str
    tidy: pd.DataFrame


def _tidy_result(result, model_name: str, n: int, adjusted_r2: float | None = None) -> pd.DataFrame:
    ci = result.conf_int()
    rows = []
    for term in result.params.index:
        rows.append(
            {
                "model": model_name,
                "term": term,
                "estimate": float(result.params[term]),
                "ci_low": float(ci.loc[term, 0]),
                "ci_high": float(ci.loc[term, 1]),
                "p_value": float(result.pvalues[term]) if term in result.pvalues else math.nan,
                "n": n,
                "r_squared": float(getattr(result, "rsquared", math.nan)),
                "adj_r_squared": float(adjusted_r2 if adjusted_r2 is not None else getattr(result, "rsquared_adj", math.nan)),
                "stability": "exploratory_unstable" if n < 30 else "standard",
            }
        )
    return pd.DataFrame(rows)


def _scale_term_ci(row: pd.Series, scale: float) -> pd.Series:
    out = row.copy()
    out["std_beta"] = float(out["estimate"] * scale)
    out["estimate"] = out["std_beta"]
    out["ci_low"] = float(out["ci_low"] * scale)
    out["ci_high"] = float(out["ci_high"] * scale)
    return out


def fit_prompt_trajectory_model(assignment_df: pd.DataFrame) -> ModelSummary:
    frame = assignment_df.dropna(subset=["prompt_score"]).copy()
    frame["assignment"] = frame["assignment"].astype(int).astype(str)
    formula = "prompt_score ~ group * C(assignment)"
    try:
        model = smf.mixedlm(formula, data=frame, groups=frame["participant_key"])
        result = model.fit(reml=False, disp=False)
        if not bool(getattr(result, "converged", True)):
            raise ValueError("MixedLM did not converge")
        tidy = _tidy_result(result, "prompt_trajectory_mixedlm", len(frame))
        method = "mixedlm"
    except (ValueError, np.linalg.LinAlgError) as exc:
        result = smf.ols(formula, data=frame).fit(cov_type="cluster", cov_kwds={"groups": frame["participant_key"]})
        tidy = _tidy_result(result, "prompt_trajectory_clustered_ols", len(frame))
        tidy["warning"] = f"MixedLM failed; used clustered OLS fallback: {exc}"
        method = "clustered_ols_fallback"
    return ModelSummary(formula=formula, n_observations=len(frame), n_participants=frame["participant_key"].nunique(), method=method, tidy=tidy)


def estimate_prompt_trajectory_means(assignment_df: pd.DataFrame, model_result: ModelSummary | None = None) -> pd.DataFrame:
    rows = []
    for (group, assignment), part in assignment_df.groupby(["group", "assignment"], sort=True):
        stat = mean_ci_bootstrap(part["prompt_score"].dropna(), n_boot=1000)
        rows.append({"group": group, "assignment": int(assignment), **stat})
    return pd.DataFrame(rows).sort_values(["group", "assignment"])


def _contrast_rows(df: pd.DataFrame, value: str) -> list[dict[str, float | str]]:
    rows = []
    pairs = [("C", "A"), ("C", "B"), ("B", "A")]
    pooled = df.assign(group_pooled=np.where(df["group"] == "C", "C", "pooled_A_B"))
    def contrast_p_value(a: pd.Series, b: pd.Series) -> float:
        if len(a) < 1 or len(b) < 1:
            return float("nan")
        observed = abs(float(a.mean() - b.mean()))
        combined = np.concatenate([a.to_numpy(), b.to_numpy()])
        labels = np.array([0] * len(a) + [1] * len(b))
        rng = np.random.default_rng(int("2026" + "0615"))
        count = 0
        n_perm = 2000
        for _ in range(n_perm):
            perm = rng.permutation(labels)
            diff = abs(float(combined[perm == 0].mean() - combined[perm == 1].mean()))
            count += diff >= observed
        return float((count + 1) / (n_perm + 1))
    for left, right in pairs:
        a = df.loc[df["group"] == left, value].dropna()
        b = df.loc[df["group"] == right, value].dropna()
        effect = hedges_g(a, b, n_boot=1000)
        diff = mean_ci_bootstrap(a, n_boot=1000)["mean"] - mean_ci_bootstrap(b, n_boot=1000)["mean"]
        p_value = contrast_p_value(a, b)
        rows.append({"contrast": f"{left} vs {right}", "mean_difference": diff, "hedges_g": effect["estimate"], "ci_low": effect["ci_low"], "ci_high": effect["ci_high"], "p_value": p_value, "n": int(len(a) + len(b))})
    a = pooled.loc[pooled["group_pooled"] == "C", value].dropna()
    b = pooled.loc[pooled["group_pooled"] == "pooled_A_B", value].dropna()
    effect = hedges_g(a, b, n_boot=1000)
    p_value = contrast_p_value(a, b)
    rows.append({"contrast": "C vs pooled A+B", "mean_difference": float(a.mean() - b.mean()), "hedges_g": effect["estimate"], "ci_low": effect["ci_low"], "ci_high": effect["ci_high"], "p_value": p_value, "n": int(len(a) + len(b))})
    return rows


def participant_level_training_effect(participant_df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    summary = group_summary_ci(participant_df, "group", "mean_prompt_score")
    summary.insert(0, "metric", "mean_prompt_score")
    summary["n_participants"] = len(participant_df)
    tests = pd.DataFrame(
        [
            {"test": "welch_anova", **welch_anova(participant_df, "group", "mean_prompt_score")},
            {"test": "kruskal_wallis", **kruskal_test(participant_df, "group", "mean_prompt_score")},
            {"test": "permutation_anova", **permutation_anova(participant_df, "group", "mean_prompt_score", n_perm=1000)},
        ]
    )
    contrasts = pd.DataFrame(_contrast_rows(participant_df, "mean_prompt_score"))
    return {"summary": summary, "tests": tests, "contrasts": contrasts}


def learning_outcome_models(participant_df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    frame = participant_df.copy()
    corrs = []
    for outcome in ["midterm_points", "final_points"]:
        pearson = pearson_with_fisher_ci(frame["mean_prompt_score"], frame[outcome])
        spearman = spearman_with_ci(frame["mean_prompt_score"], frame[outcome], n_boot=1000)
        corrs.append({"metric": f"mean_prompt_score vs {outcome}", "method": "pearson", **pearson})
        corrs.append({"metric": f"mean_prompt_score vs {outcome}", "method": "spearman", **spearman})
    models = []
    work = frame.dropna(subset=["final_points", "mean_prompt_score", "midterm_points"]).copy()
    if "prior_chatgpt_use_score" not in work.columns:
        work["prior_chatgpt_use_score"] = pd.to_numeric(work.get("prior_chatgpt_use", np.nan), errors="coerce")
    formula = "final_points ~ mean_prompt_score + midterm_points + group + prior_chatgpt_use_score"
    result = smf.ols(formula, data=work).fit(cov_type="HC3")
    tidy = _tidy_result(result, "final_points", int(result.nobs))
    y_sd = work["final_points"].std(ddof=1)
    for term in ["mean_prompt_score", "midterm_points", "prior_chatgpt_use_score"]:
        if term in tidy["term"].to_numpy() and y_sd and np.isfinite(y_sd):
            scale = work[term].std(ddof=1) / y_sd
            tidy.loc[tidy["term"] == term, "std_beta"] = tidy.loc[tidy["term"] == term, "estimate"] * scale
    models.append(tidy)
    work["grade_change"] = work["final_points"] - work["midterm_points"]
    result2 = smf.ols("grade_change ~ mean_prompt_score + group + prior_chatgpt_use_score", data=work).fit(cov_type="HC3")
    tidy2 = _tidy_result(result2, "grade_change", int(result2.nobs))
    y_sd = work["grade_change"].std(ddof=1)
    for term in ["mean_prompt_score", "prior_chatgpt_use_score"]:
        if term in tidy2["term"].to_numpy() and y_sd and np.isfinite(y_sd):
            scale = work[term].std(ddof=1) / y_sd
            tidy2.loc[tidy2["term"] == term, "std_beta"] = tidy2.loc[tidy2["term"] == term, "estimate"] * scale
    models.append(tidy2)
    return {"correlations": pd.DataFrame(corrs), "models": pd.concat(models, ignore_index=True)}


def perceived_usefulness_models(participant_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    frame = participant_df.copy()
    if "prior_chatgpt_use_score" not in frame.columns:
        frame["prior_chatgpt_use_score"] = pd.to_numeric(frame.get("prior_chatgpt_use", np.nan), errors="coerce")
    for model_name, formula in [
        ("final_points", "final_points ~ perceived_usefulness + midterm_points + group + prior_chatgpt_use_score"),
        ("grade_change", "grade_change ~ perceived_usefulness + group + prior_chatgpt_use_score"),
    ]:
        work = frame.copy()
        work["grade_change"] = work["final_points"] - work["midterm_points"]
        needed = ["perceived_usefulness", "prior_chatgpt_use_score", "group", "final_points"]
        if model_name == "final_points":
            needed.append("midterm_points")
        else:
            needed.append("grade_change")
        work = work.dropna(subset=needed).copy()
        work["perceived_usefulness_z"] = standardize_series(work["perceived_usefulness"])
        formula_z = formula.replace("perceived_usefulness", "perceived_usefulness_z")
        result = smf.ols(formula_z, data=work).fit(cov_type="HC3")
        tidy = _tidy_result(result, model_name, int(result.nobs))
        row = tidy[tidy["term"] == "perceived_usefulness_z"].copy()
        y_sd = work[model_name].std(ddof=1)
        if y_sd and np.isfinite(y_sd):
            row = row.apply(lambda r: _scale_term_ci(r, 1 / y_sd), axis=1)
        rows.append(row)
    return pd.concat(rows, ignore_index=True)


def calibration_models(participant_df: pd.DataFrame) -> pd.DataFrame:
    dimensions = [
        "trust", "perceived_usefulness", "perceived_ease_of_use", "behavioral_intention",
        "hedonic_motivation", "locus_of_control", "facilitating_conditions", "social_influence", "attitude",
    ]
    rows = []
    frame = participant_df.copy()
    if "prior_chatgpt_use_score" not in frame.columns:
        frame["prior_chatgpt_use_score"] = pd.to_numeric(frame.get("prior_chatgpt_use", np.nan), errors="coerce")
    for dim in dimensions:
        if dim not in frame.columns:
            continue
        work = frame.dropna(subset=["mean_prompt_score", dim, "group", "prior_chatgpt_use_score"]).copy()
        work[f"{dim}_z"] = standardize_series(work[dim])
        result = smf.ols(f"mean_prompt_score ~ {dim}_z + group + prior_chatgpt_use_score", data=work).fit(cov_type="HC3")
        tidy = _tidy_result(result, dim, int(result.nobs))
        row = tidy[tidy["term"] == f"{dim}_z"].copy()
        y_sd = work["mean_prompt_score"].std(ddof=1)
        if y_sd and np.isfinite(y_sd):
            row = row.apply(lambda r: _scale_term_ci(r, 1 / y_sd), axis=1)
        row["dimension"] = dim
        rows.append(row)
    out = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    if not out.empty:
        out["fdr_p_value"] = benjamini_hochberg(out["p_value"])
    return out


def prepost_survey_change_models(composites: pd.DataFrame) -> pd.DataFrame:
    dims = [c for c in composites.columns if c not in {"participant_key", "phase"} and not c.endswith("_items_present")]
    rows = []
    for dim in dims:
        wide = composites.pivot_table(index="participant_key", columns="phase", values=dim, aggfunc="mean")
        if {"pre", "post"} <= set(wide.columns):
            diff = wide["post"] - wide["pre"]
            stat = mean_ci_bootstrap(diff, n_boot=1000)
            paired = diff.dropna()
            p_value = float(stats.ttest_rel(wide.loc[paired.index, "post"], wide.loc[paired.index, "pre"], nan_policy="omit").pvalue) if len(paired) > 1 else float("nan")
            rows.append({"dimension": dim, "pre_mean": float(wide["pre"].mean()), "post_mean": float(wide["post"].mean()), "change": stat["mean"], "ci_low": stat["ci_low"], "ci_high": stat["ci_high"], "n": int(paired.shape[0]), "phase_p_value": p_value, "interaction_p_value": float("nan")})
    out = pd.DataFrame(rows)
    if not out.empty:
        out["fdr_p_value"] = benjamini_hochberg(out["phase_p_value"])
    return out


def model_based_learning_prediction_table(participant_df: pd.DataFrame) -> pd.DataFrame:
    frame = participant_df.copy()
    if "prior_chatgpt_use_score" not in frame.columns:
        frame["prior_chatgpt_use_score"] = pd.to_numeric(frame.get("prior_chatgpt_use", np.nan), errors="coerce")
    work = frame.dropna(subset=["final_points", "mean_prompt_score", "midterm_points", "group", "prior_chatgpt_use_score"]).copy()
    if work.empty or work["mean_prompt_score"].nunique() < 2:
        return pd.DataFrame({"mean_prompt_score": [], "predicted_final_points": [], "ci_low": [], "ci_high": []})
    result = smf.ols("final_points ~ mean_prompt_score + midterm_points + group + prior_chatgpt_use_score", data=work).fit(cov_type="HC3")
    x = np.linspace(work["mean_prompt_score"].min(), work["mean_prompt_score"].max(), 30)
    reference = {
        "mean_prompt_score": x,
        "midterm_points": work["midterm_points"].mean(),
        "group": work["group"].mode().iloc[0],
        "prior_chatgpt_use_score": work["prior_chatgpt_use_score"].mean(),
    }
    pred = result.get_prediction(pd.DataFrame(reference)).summary_frame(alpha=0.05)
    return pd.DataFrame(
        {
            "mean_prompt_score": x,
            "predicted_final_points": pred["mean"].to_numpy(),
            "ci_low": pred["mean_ci_lower"].to_numpy(),
            "ci_high": pred["mean_ci_upper"].to_numpy(),
        }
    )
