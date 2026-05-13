from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import numpy as np
import pandas as pd
from scipy import stats

from genai_literacy_trial.scales import GRADE_POINTS, LIKERT_POINTS

PROMPT_SCORE_COLUMN = "Student prompting quality score (1 bad - 5 best)"
LOCUS_OF_CONTROL_COLUMNS = [
    " [I feel like I control what happens while working with ChatGPT because I use it as I want and get what I want]",
    " [When using ChatGPT, the primary responsibility to get what I want belongs to ChatGPT, not to me]",
    " [When using ChatGPT, I can retain attention and interest in this activity longer than when using other information search systems such as Google or Stack Overflow]",
    " [Time seems to pass quickly while I am using ChatGPT]",
]

PAPER_TARGETS: dict[str, float] = {
    "students_before": 55,
    "students_after": 45,
    "dropouts": 10,
    "retained_students": 45,
    "section_midterm_anova_p": 0.7349953162884579,
    "section_final_anova_p": 0.41520597213777033,
    "prompt_training_anova_p": 0.00174,
    "prompt_score_grade_midterm_r": 0.2887452333645939,
    "prompt_score_grade_midterm_p": 0.005779497349069233,
    "prompt_score_grade_final_r": 0.4508356204428825,
    "prompt_score_grade_final_p": 8.228481058326196e-06,
    "prompt_score_locus_control_before_r": -0.569,
}


def convert_letter_grade(value: object) -> float:
    if value is None:
        return np.nan
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return np.nan
    return GRADE_POINTS.get(text, np.nan)


def filter_complete_pre_post(
    survey: pd.DataFrame,
    *,
    email_col: str = "Email",
    phase_col: str = "Phase",
    before_value: str = "Before",
    after_value: str = "After",
) -> tuple[pd.DataFrame, dict[str, int]]:
    before = set(survey.loc[survey[phase_col] == before_value, email_col].dropna())
    after = set(survey.loc[survey[phase_col] == after_value, email_col].dropna())
    retained = before & after
    dropouts = before - after
    filtered = survey[survey[email_col].isin(retained)].copy()
    summary = {
        "students_before": len(before),
        "students_after": len(after),
        "dropouts": len(dropouts),
        "retained_students": len(retained),
    }
    return filtered, summary


def mean_prompt_scores(prompts: pd.DataFrame) -> pd.DataFrame:
    required = ["Email", PROMPT_SCORE_COLUMN]
    missing = [column for column in required if column not in prompts.columns]
    if missing:
        raise ValueError(f"Missing required prompt columns: {', '.join(missing)}")
    result = (
        prompts[required]
        .dropna(subset=["Email", PROMPT_SCORE_COLUMN])
        .groupby("Email", as_index=False)[PROMPT_SCORE_COLUMN]
        .mean()
        .rename(columns={PROMPT_SCORE_COLUMN: "mean_prompt_score"})
    )
    return result


def optional_locus_control_before(survey: pd.DataFrame, prompt_scores: pd.DataFrame) -> dict[str, float]:
    if "Phase" not in survey.columns:
        return {}
    if not set(LOCUS_OF_CONTROL_COLUMNS) <= set(survey.columns):
        return {}
    before = survey[survey["Phase"] == "Before"].copy()
    for column in LOCUS_OF_CONTROL_COLUMNS:
        before[column] = before[column].map(LIKERT_POINTS)
    before["locus_of_control"] = before[LOCUS_OF_CONTROL_COLUMNS].mean(axis=1)
    merged = prompt_scores.merge(before[["Email", "locus_of_control"]], on="Email", how="inner")
    stat = pearson_stat(merged["mean_prompt_score"], merged["locus_of_control"])
    return {
        "prompt_score_locus_control_before_r": stat["correlation"],
        "prompt_score_locus_control_before_p": stat["p_value"],
        "prompt_score_locus_control_before_n": stat["n"],
    }


def pearson_stat(x: pd.Series | np.ndarray, y: pd.Series | np.ndarray) -> dict[str, float]:
    frame = pd.DataFrame({"x": x, "y": y}).dropna()
    if len(frame) < 2:
        return {"correlation": np.nan, "p_value": np.nan, "n": float(len(frame))}
    correlation, p_value = stats.pearsonr(frame["x"], frame["y"])
    return {"correlation": float(correlation), "p_value": float(p_value), "n": float(len(frame))}


def anova_by_group(data: pd.DataFrame, *, value: str, group: str) -> dict[str, float]:
    groups = [
        series.dropna().to_numpy()
        for _, series in data[[group, value]].dropna().groupby(group, sort=True)[value]
    ]
    groups = [values for values in groups if len(values) > 0]
    if len(groups) < 2 or all(len(values) < 2 for values in groups):
        return {"statistic": np.nan, "p_value": np.nan, "groups": float(len(groups))}
    statistic, p_value = stats.f_oneway(*groups)
    return {"statistic": float(statistic), "p_value": float(p_value), "groups": float(len(groups))}


def build_paper_aggregates(
    *,
    survey: pd.DataFrame,
    prompts: pd.DataFrame,
    grades: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    prompt_scores = mean_prompt_scores(prompts)
    grade_frame = grades[["Email", "Group", "Midterm Grade", "Final Grade"]].copy()
    grade_frame["midterm_points"] = grade_frame["Midterm Grade"].map(convert_letter_grade)
    grade_frame["final_points"] = grade_frame["Final Grade"].map(convert_letter_grade)
    merged = prompt_scores.merge(grade_frame, on="Email", how="inner")

    if "Phase" in survey.columns:
        _, sample_summary = filter_complete_pre_post(survey)
    else:
        sample_summary = {"retained_students": int(survey["Email"].nunique()) if "Email" in survey.columns else len(survey)}

    prompt_training_means = (
        merged.groupby("Group", as_index=False)
        .agg(
            mean_prompt_score=("mean_prompt_score", "mean"),
            mean_midterm_points=("midterm_points", "mean"),
            mean_final_points=("final_points", "mean"),
            n=("mean_prompt_score", "size"),
        )
        .sort_values("Group")
    )

    correlations = pd.DataFrame(
        [
            {"metric": "prompt_score_midterm", **pearson_stat(merged["mean_prompt_score"], merged["midterm_points"])},
            {"metric": "prompt_score_final", **pearson_stat(merged["mean_prompt_score"], merged["final_points"])},
        ]
    )
    paper_statistics = paper_observed_statistics(
        sample_summary=sample_summary,
        merged=merged,
        locus_control=optional_locus_control_before(survey, prompt_scores),
    )

    return {
        "sample_summary": pd.DataFrame([sample_summary]),
        "prompt_training_means": prompt_training_means,
        "prompt_grade_correlations": correlations,
        "paper_statistics": paper_statistics,
    }


def validate_against_targets(observed: Mapping[str, float], *, tolerance: float = 1e-3) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for metric, expected in PAPER_TARGETS.items():
        actual = observed.get(metric, np.nan)
        if pd.isna(actual):
            status = "missing"
            delta = np.nan
        else:
            delta = float(actual) - float(expected)
            status = "ok" if abs(delta) <= tolerance else "mismatch"
        rows.append({"metric": metric, "expected": expected, "observed": actual, "delta": delta, "status": status})
    return pd.DataFrame(rows)


def paper_observed_statistics(
    *,
    sample_summary: Mapping[str, int],
    merged: pd.DataFrame,
    locus_control: Mapping[str, float] | None = None,
) -> pd.DataFrame:
    section_midterm = anova_by_group(merged, value="midterm_points", group="Group")
    section_final = anova_by_group(merged, value="final_points", group="Group")
    prompt_training = anova_by_group(merged, value="mean_prompt_score", group="Group")
    prompt_midterm = pearson_stat(merged["mean_prompt_score"], merged["midterm_points"])
    prompt_final = pearson_stat(merged["mean_prompt_score"], merged["final_points"])
    means = merged.groupby("Group")["mean_prompt_score"].mean()

    observed: dict[str, float] = {
        **{key: float(value) for key, value in sample_summary.items()},
        "section_midterm_anova_p": section_midterm["p_value"],
        "section_final_anova_p": section_final["p_value"],
        "prompt_training_anova_p": prompt_training["p_value"],
        "prompt_score_grade_midterm_r": prompt_midterm["correlation"],
        "prompt_score_grade_midterm_p": prompt_midterm["p_value"],
        "prompt_score_grade_midterm_n": prompt_midterm["n"],
        "prompt_score_grade_final_r": prompt_final["correlation"],
        "prompt_score_grade_final_p": prompt_final["p_value"],
        "prompt_score_grade_final_n": prompt_final["n"],
    }
    for group, value in means.items():
        observed[f"prompt_mean_group_{group}"] = float(value)
    if locus_control:
        observed.update({key: float(value) for key, value in locus_control.items()})
    return pd.DataFrame([{"metric": key, "observed": value} for key, value in observed.items()])


def write_aggregate_outputs(outputs: Mapping[str, pd.DataFrame], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, table in outputs.items():
        table.to_csv(output_dir / f"{name}.csv", index=False)


@dataclass(frozen=True)
class InputPaths:
    survey: Path
    grades: Path
    prompts: Path


def load_csv_inputs(input_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    paths = InputPaths(
        survey=input_dir / "survey.csv",
        grades=input_dir / "grades.csv",
        prompts=input_dir / "prompts.csv",
    )
    missing = [str(path) for path in (paths.survey, paths.grades, paths.prompts) if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing input CSV files: " + ", ".join(missing))
    return pd.read_csv(paths.survey), pd.read_csv(paths.grades), pd.read_csv(paths.prompts)


def observed_metrics_from_outputs(outputs: Mapping[str, pd.DataFrame]) -> dict[str, float]:
    observed: dict[str, float] = {}
    paper_statistics = outputs.get("paper_statistics")
    if paper_statistics is not None and {"metric", "observed"} <= set(paper_statistics.columns):
        return {
            str(row["metric"]): float(row["observed"])
            for _, row in paper_statistics.dropna(subset=["observed"]).iterrows()
        }
    sample = outputs.get("sample_summary")
    if sample is not None and not sample.empty:
        for column in sample.columns:
            value = sample[column].iloc[0]
            if pd.notna(value):
                observed[column] = float(value)
    return observed
