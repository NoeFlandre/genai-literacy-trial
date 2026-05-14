from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.formula.api as smf

from genai_literacy_trial.quant_schema import (
    LearningOutcomeTables,
    NORMALIZED_POST_LABEL,
    NORMALIZED_PRE_LABEL,
    PARTICIPANT_KEY_COLUMN,
    PromptSensitivityTables,
    TrainingEffectTables,
)
from genai_literacy_trial.quant_stats import (
    benjamini_hochberg,
    DEFAULT_SEED,
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


CALIBRATION_DIMENSIONS = (
    "trust",
    "perceived_usefulness",
    "perceived_ease_of_use",
    "behavioral_intention",
    "hedonic_motivation",
    "locus_of_control",
    "facilitating_conditions",
    "social_influence",
    "attitude",
)


@dataclass
class ModelSummary:
    formula: str
    n_observations: int
    n_participants: int
    method: str
    tidy: pd.DataFrame


def _canonical_group(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    if "group" not in out.columns and "group_x" in out.columns:
        out = out.rename(columns={"group_x": "group"})
    if "group_y" in out.columns:
        out = out.drop(columns=["group_y"])
    return out


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


def _ensure_prior_use_score(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    if "prior_chatgpt_use_score" not in out.columns:
        out["prior_chatgpt_use_score"] = pd.to_numeric(out.get("prior_chatgpt_use", np.nan), errors="coerce")
    return out


def _complete_cases(frame: pd.DataFrame, required: list[str]) -> pd.DataFrame:
    return frame.dropna(subset=required).copy()


def _fit_ols_hc3(formula: str, data: pd.DataFrame):
    return smf.ols(formula, data=data).fit(cov_type="HC3")


def _add_standardized_effect(
    tidy: pd.DataFrame,
    work: pd.DataFrame,
    term: str,
    outcome: str,
    *,
    from_standardized_predictor: bool,
    include_ci: bool,
) -> pd.DataFrame:
    if term not in tidy["term"].to_numpy():
        return tidy
    out = tidy.copy()
    y_sd = work[outcome].std(ddof=1)
    if not y_sd or not np.isfinite(y_sd):
        return out
    if from_standardized_predictor:
        scale = 1.0 / y_sd
    else:
        x_sd = work[term].std(ddof=1)
        if not x_sd or not np.isfinite(x_sd):
            return out
        scale = x_sd / y_sd
    mask = out["term"] == term
    out.loc[mask, "std_beta"] = out.loc[mask, "estimate"] * scale
    if include_ci:
        out.loc[mask, "std_ci_low"] = out.loc[mask, "ci_low"] * scale
        out.loc[mask, "std_ci_high"] = out.loc[mask, "ci_high"] * scale
    return out


def _model_diagnostics(frame: pd.DataFrame, model: str, required: list[str], survey_composite: str | None = None) -> dict[str, int | str]:
    grade_change_required = "grade_change" in required
    out: dict[str, int | str] = {
        "model": model,
        "starting_n": int(len(frame)),
        "final_n": int(len(frame.dropna(subset=required))),
        "loss_type": "marginal_non_additive",
        "lost_final_grade": int(frame["final_points"].isna().sum()) if ("final_points" in required or grade_change_required) and "final_points" in frame else 0,
        "lost_midterm_grade": int(frame["midterm_points"].isna().sum()) if ("midterm_points" in required or grade_change_required) and "midterm_points" in frame else 0,
        "lost_mean_prompt_score": int(frame["mean_prompt_score"].isna().sum()) if "mean_prompt_score" in required and "mean_prompt_score" in frame else 0,
        "lost_prior_chatgpt_use_score": int(frame["prior_chatgpt_use_score"].isna().sum()) if "prior_chatgpt_use_score" in required and "prior_chatgpt_use_score" in frame else 0,
        "lost_survey_composite": int(frame[survey_composite].isna().sum()) if survey_composite and survey_composite in frame else 0,
        "lost_group": int(frame["group"].isna().sum()) if "group" in required and "group" in frame else 0,
    }
    return out


def fit_prompt_trajectory_model(assignment_df: pd.DataFrame) -> ModelSummary:
    frame = assignment_df.dropna(subset=["prompt_score"]).copy()
    frame["assignment"] = frame["assignment"].astype(int).astype(str)
    formula = "prompt_score ~ group * C(assignment)"
    try:
        model = smf.mixedlm(formula, data=frame, groups=frame[PARTICIPANT_KEY_COLUMN])
        result = model.fit(reml=False, disp=False)
        if not bool(getattr(result, "converged", True)):
            raise ValueError("MixedLM did not converge")
        tidy = _tidy_result(result, "prompt_trajectory_mixedlm", len(frame))
        method = "mixedlm"
    except (ValueError, np.linalg.LinAlgError) as exc:
        result = smf.ols(formula, data=frame).fit(cov_type="cluster", cov_kwds={"groups": frame[PARTICIPANT_KEY_COLUMN]})
        tidy = _tidy_result(result, "prompt_trajectory_clustered_ols", len(frame))
        tidy["warning"] = f"MixedLM failed; used clustered OLS fallback: {exc}"
        method = "clustered_ols_fallback"
    return ModelSummary(formula=formula, n_observations=len(frame), n_participants=frame[PARTICIPANT_KEY_COLUMN].nunique(), method=method, tidy=tidy)


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
        rng = np.random.default_rng(DEFAULT_SEED)
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
        diff_stat = _mean_difference_ci(a, b)
        p_value = contrast_p_value(a, b)
        rows.append({"contrast": f"{left} vs {right}", **diff_stat, "hedges_g": effect["estimate"], "hedges_g_ci_low": effect["ci_low"], "hedges_g_ci_high": effect["ci_high"], "p_value": p_value, "n": int(len(a) + len(b))})
    a = pooled.loc[pooled["group_pooled"] == "C", value].dropna()
    b = pooled.loc[pooled["group_pooled"] == "pooled_A_B", value].dropna()
    effect = hedges_g(a, b, n_boot=1000)
    p_value = contrast_p_value(a, b)
    rows.append({"contrast": "C vs pooled A+B", **_mean_difference_ci(a, b), "hedges_g": effect["estimate"], "hedges_g_ci_low": effect["ci_low"], "hedges_g_ci_high": effect["ci_high"], "p_value": p_value, "n": int(len(a) + len(b))})
    return rows


def _mean_difference_ci(a: pd.Series, b: pd.Series, seed: int = DEFAULT_SEED, n_boot: int = 1000) -> dict[str, float]:
    x = pd.Series(a).dropna().astype(float).to_numpy()
    y = pd.Series(b).dropna().astype(float).to_numpy()
    if len(x) == 0 or len(y) == 0:
        return {"mean_difference": math.nan, "mean_difference_ci_low": math.nan, "mean_difference_ci_high": math.nan}
    rng = np.random.default_rng(seed)
    boots = rng.choice(x, size=(n_boot, len(x)), replace=True).mean(axis=1) - rng.choice(y, size=(n_boot, len(y)), replace=True).mean(axis=1)
    return {"mean_difference": float(x.mean() - y.mean()), "mean_difference_ci_low": float(np.quantile(boots, 0.025)), "mean_difference_ci_high": float(np.quantile(boots, 0.975))}


def participant_level_training_effect(participant_df: pd.DataFrame) -> TrainingEffectTables:
    participant_df = _canonical_group(participant_df)
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


def learning_outcome_models(participant_df: pd.DataFrame) -> LearningOutcomeTables:
    frame = _canonical_group(participant_df)
    frame = _ensure_prior_use_score(frame)
    corrs = []
    for outcome in ["midterm_points", "final_points"]:
        pearson = pearson_with_fisher_ci(frame["mean_prompt_score"], frame[outcome])
        spearman = spearman_with_ci(frame["mean_prompt_score"], frame[outcome], n_boot=1000)
        corrs.append({"metric": f"mean_prompt_score vs {outcome}", "method": "pearson", **pearson})
        corrs.append({"metric": f"mean_prompt_score vs {outcome}", "method": "spearman", **spearman})
    models = []
    work = _complete_cases(frame, ["final_points", "mean_prompt_score", "midterm_points", "group", "prior_chatgpt_use_score"])
    formula = "final_points ~ mean_prompt_score + midterm_points + group + prior_chatgpt_use_score"
    result = _fit_ols_hc3(formula, work)
    tidy = _tidy_result(result, "final_points", int(result.nobs))
    tidy = _add_standardized_effect(tidy, work, "mean_prompt_score", "final_points", from_standardized_predictor=False, include_ci=False)
    tidy = _add_standardized_effect(tidy, work, "midterm_points", "final_points", from_standardized_predictor=False, include_ci=False)
    tidy = _add_standardized_effect(
        tidy,
        work,
        "prior_chatgpt_use_score",
        "final_points",
        from_standardized_predictor=False,
        include_ci=False,
    )
    models.append(tidy)
    work["grade_change"] = work["final_points"] - work["midterm_points"]
    result2 = _fit_ols_hc3("grade_change ~ mean_prompt_score + group + prior_chatgpt_use_score", work)
    tidy2 = _tidy_result(result2, "grade_change", int(result2.nobs))
    tidy2 = _add_standardized_effect(tidy2, work, "mean_prompt_score", "grade_change", from_standardized_predictor=False, include_ci=False)
    tidy2 = _add_standardized_effect(
        tidy2,
        work,
        "prior_chatgpt_use_score",
        "grade_change",
        from_standardized_predictor=False,
        include_ci=False,
    )
    models.append(tidy2)
    return {"correlations": pd.DataFrame(corrs), "models": pd.concat(models, ignore_index=True)}


def complete_case_diagnostics(participant_df: pd.DataFrame) -> pd.DataFrame:
    frame = _canonical_group(participant_df)
    if "prior_chatgpt_use_score" not in frame.columns:
        frame["prior_chatgpt_use_score"] = pd.to_numeric(frame.get("prior_chatgpt_use", np.nan), errors="coerce")
    rows = [
        _model_diagnostics(frame, "final_points", ["final_points", "mean_prompt_score", "midterm_points", "group", "prior_chatgpt_use_score"]),
        _model_diagnostics(frame.assign(grade_change=frame["final_points"] - frame["midterm_points"]), "grade_change", ["grade_change", "mean_prompt_score", "group", "prior_chatgpt_use_score"]),
        _model_diagnostics(frame, "perceived_usefulness_final_points", ["final_points", "midterm_points", "perceived_usefulness", "group", "prior_chatgpt_use_score"], "perceived_usefulness"),
        _model_diagnostics(frame.assign(grade_change=frame["final_points"] - frame["midterm_points"]), "perceived_usefulness_grade_change", ["grade_change", "perceived_usefulness", "group", "prior_chatgpt_use_score"], "perceived_usefulness"),
    ]
    for dim in CALIBRATION_DIMENSIONS:
        if dim in frame.columns:
            rows.append(_model_diagnostics(frame, f"calibration_{dim}", ["mean_prompt_score", dim, "group", "prior_chatgpt_use_score"], dim))
    return pd.DataFrame(rows)


def perceived_usefulness_models(participant_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    frame = _canonical_group(participant_df)
    frame = _ensure_prior_use_score(frame)
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
        work = _complete_cases(work, needed)
        work["perceived_usefulness_z"] = standardize_series(work["perceived_usefulness"])
        formula_z = formula.replace("perceived_usefulness", "perceived_usefulness_z")
        result = _fit_ols_hc3(formula_z, work)
        tidy = _tidy_result(result, model_name, int(result.nobs))
        row = tidy[tidy["term"] == "perceived_usefulness_z"].copy()
        row = _add_standardized_effect(
            row,
            work,
            "perceived_usefulness_z",
            model_name,
            from_standardized_predictor=True,
            include_ci=True,
        )
        rows.append(row)
    return pd.concat(rows, ignore_index=True)


def calibration_models(participant_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    frame = _canonical_group(participant_df)
    frame = _ensure_prior_use_score(frame)
    for dim in CALIBRATION_DIMENSIONS:
        if dim not in frame.columns:
            continue
        work = _complete_cases(frame, ["mean_prompt_score", dim, "group", "prior_chatgpt_use_score"])
        work[f"{dim}_z"] = standardize_series(work[dim])
        result = _fit_ols_hc3(f"mean_prompt_score ~ {dim}_z + group + prior_chatgpt_use_score", work)
        tidy = _tidy_result(result, dim, int(result.nobs))
        row = tidy[tidy["term"] == f"{dim}_z"].copy()
        row = _add_standardized_effect(
            row,
            work,
            f"{dim}_z",
            "mean_prompt_score",
            from_standardized_predictor=True,
            include_ci=True,
        )
        row["dimension"] = dim
        rows.append(row)
    out = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    if not out.empty:
        out["fdr_p_value"] = benjamini_hochberg(out["p_value"])
    return out


def prepost_survey_change_models(composites: pd.DataFrame) -> pd.DataFrame:
    composites = composites.copy()
    if "group" not in composites.columns and "group_x" in composites.columns:
        composites = composites.rename(columns={"group_x": "group"})
    if "group" not in composites.columns:
        raise ValueError("pre/post survey change models require group in the composite table")
    dims = [
        c
        for c in composites.columns
        if c not in {PARTICIPANT_KEY_COLUMN, "phase", "group", "prior_chatgpt_use_score"} and not c.endswith("_items_present")
    ]
    rows = []
    for dim in dims:
        long = composites[[PARTICIPANT_KEY_COLUMN, "phase", "group", dim]].dropna().copy()
        try:
            result = smf.mixedlm(f"{dim} ~ phase * group", data=long, groups=long[PARTICIPANT_KEY_COLUMN]).fit(reml=False, disp=False)
            if not bool(getattr(result, "converged", True)):
                raise ValueError("MixedLM did not converge")
            tidy = _tidy_result(result, f"prepost_{dim}", int(result.nobs))
            is_interaction = tidy["term"].str.contains(":")
            phase_rows = tidy[tidy["term"].str.startswith("phase") & ~is_interaction]
            interaction_rows = tidy[is_interaction]
            wide = composites.pivot_table(index=PARTICIPANT_KEY_COLUMN, columns="phase", values=dim, aggfunc="mean")
            diff = wide[NORMALIZED_POST_LABEL] - wide[NORMALIZED_PRE_LABEL] if {NORMALIZED_PRE_LABEL, NORMALIZED_POST_LABEL} <= set(wide.columns) else pd.Series(dtype=float)
            stat = mean_ci_bootstrap(diff, n_boot=1000)
            rows.append({"dimension": dim, "analysis_type": "mixed_model", "pre_mean": float(wide.get(NORMALIZED_PRE_LABEL, pd.Series(dtype=float)).mean()), "post_mean": float(wide.get(NORMALIZED_POST_LABEL, pd.Series(dtype=float)).mean()), "change": stat["mean"], "ci_low": stat["ci_low"], "ci_high": stat["ci_high"], "n": int(long[PARTICIPANT_KEY_COLUMN].nunique()), "phase_p_value": float(phase_rows["p_value"].min()) if not phase_rows.empty else math.nan, "interaction_p_value": float(interaction_rows["p_value"].min()) if not interaction_rows.empty else math.nan})
        except (ValueError, np.linalg.LinAlgError):
            wide = composites.pivot_table(index=PARTICIPANT_KEY_COLUMN, columns="phase", values=dim, aggfunc="mean")
            if not {NORMALIZED_PRE_LABEL, NORMALIZED_POST_LABEL} <= set(wide.columns):
                continue
            diff = wide[NORMALIZED_POST_LABEL] - wide[NORMALIZED_PRE_LABEL]
            stat = mean_ci_bootstrap(diff, n_boot=1000)
            paired = diff.dropna()
            p_value = float(stats.ttest_rel(wide.loc[paired.index, NORMALIZED_POST_LABEL], wide.loc[paired.index, NORMALIZED_PRE_LABEL], nan_policy="omit").pvalue) if len(paired) > 1 else float("nan")
            rows.append({"dimension": dim, "analysis_type": "paired_descriptive_fallback", "pre_mean": float(wide[NORMALIZED_PRE_LABEL].mean()), "post_mean": float(wide[NORMALIZED_POST_LABEL].mean()), "change": stat["mean"], "ci_low": stat["ci_low"], "ci_high": stat["ci_high"], "n": int(paired.shape[0]), "phase_p_value": p_value, "interaction_p_value": float("nan")})
    out = pd.DataFrame(rows)
    if not out.empty:
        out["fdr_p_value"] = benjamini_hochberg(out["phase_p_value"])
    return out


def prompt_missingness_sensitivity(participant_df: pd.DataFrame, min_all4_n: int = 30) -> PromptSensitivityTables:
    frame = _canonical_group(participant_df)
    frame = _ensure_prior_use_score(frame)
    distribution = frame.groupby(["group", "scored_assignments"], dropna=False).size().reset_index(name="n").sort_values(["group", "scored_assignments"])

    def model_for(subset: pd.DataFrame, label: str, include_scored: bool = False) -> pd.DataFrame:
        work = subset.copy()
        work = _ensure_prior_use_score(work)
        terms = "mean_prompt_score + midterm_points + group + prior_chatgpt_use_score"
        if include_scored:
            terms += " + scored_assignments"
        work = _complete_cases(work, ["final_points", "mean_prompt_score", "midterm_points", "group", "prior_chatgpt_use_score"])
        if len(work) < 3:
            return pd.DataFrame([{"model": label, "status": "not_run_small_n", "n": int(len(work))}])
        result = _fit_ols_hc3(f"final_points ~ {terms}", work)
        out = _tidy_result(result, label, int(result.nobs))
        out["status"] = "run"
        return out

    min3 = model_for(frame[frame["scored_assignments"] >= 3], "min3_scored_assignments", include_scored=True)
    all4_subset = frame[frame["scored_assignments"] == 4]
    if len(all4_subset) < min_all4_n:
        all4 = pd.DataFrame([{"model": "all4_scored_assignments", "status": "not_run_small_n", "n": int(len(all4_subset))}])
    else:
        all4 = model_for(all4_subset, "all4_scored_assignments")
    return {"scored_assignment_distribution": distribution, "min3_assignments": min3, "all4_assignments": all4}


def model_based_learning_prediction_table(participant_df: pd.DataFrame) -> pd.DataFrame:
    frame = _canonical_group(participant_df)
    frame = _ensure_prior_use_score(frame)
    work = _complete_cases(frame, ["final_points", "mean_prompt_score", "midterm_points", "group", "prior_chatgpt_use_score"])
    if work.empty or work["mean_prompt_score"].nunique() < 2:
        return pd.DataFrame({"mean_prompt_score": [], "predicted_final_points": [], "ci_low": [], "ci_high": []})
    result = _fit_ols_hc3("final_points ~ mean_prompt_score + midterm_points + group + prior_chatgpt_use_score", work)
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
