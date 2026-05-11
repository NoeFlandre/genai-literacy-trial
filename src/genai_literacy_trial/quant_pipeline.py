from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from genai_literacy_trial.privacy import scan_public_tree
from genai_literacy_trial.quant_config import QuantConfig, load_expected_inventory, load_quant_config
from genai_literacy_trial.quant_figures import plot_calibration_forest, plot_learning_outcome, plot_prompt_quality_trajectory
from genai_literacy_trial.quant_models import (
    calibration_models,
    estimate_prompt_trajectory_means,
    fit_prompt_trajectory_model,
    learning_outcome_models,
    participant_level_training_effect,
    perceived_usefulness_models,
    prepost_survey_change_models,
)
from genai_literacy_trial.quant_preprocess import (
    build_assignment_prompt_table,
    build_participant_table,
    compute_survey_composites,
    prepare_retained_survey,
    suppress_small_cells,
    validate_analysis_inventory,
)
from genai_literacy_trial.quant_report import write_quantitative_report
from genai_literacy_trial.quant_stats import cronbach_alpha, group_summary_ci, small_sample_sensitivity


REQUIRED_TABLES = [
    "table_data_verification",
    "table_missingness_prompt_by_group_assignment",
    "table_baseline_balance",
    "table_prompt_trajectory_model",
    "table_prompt_trajectory_estimated_means",
    "table_participant_training_contrasts",
    "table_learning_outcome_models",
    "table_prompt_grade_correlations",
    "table_calibration_models",
    "table_survey_reliability",
    "table_prepost_survey_change",
    "table_small_sample_sensitivity",
    "table_perceived_usefulness_models",
]


def _read_input(input_dir: Path, name: str) -> pd.DataFrame:
    csv = input_dir / f"{name}.csv"
    xlsx = input_dir / f"{name}.xlsx"
    if csv.exists():
        return pd.read_csv(csv)
    if xlsx.exists():
        return pd.read_excel(xlsx)
    # compatibility with clean_private_data CLI input names
    alt = input_dir / f"public_cli_input_{name}.csv"
    if alt.exists():
        return pd.read_csv(alt)
    raise FileNotFoundError(f"Missing {name}.csv or {name}.xlsx in {input_dir}")


def _merge_pre_composites(participant: pd.DataFrame, composites: pd.DataFrame) -> pd.DataFrame:
    pre = composites[composites["phase"].isin(["pre", "Before"])].drop(columns=["phase"], errors="ignore")
    pre = pre.drop_duplicates("participant_key")
    return participant.merge(pre, on="participant_key", how="left")


def _baseline(participant: pd.DataFrame, config: QuantConfig) -> pd.DataFrame:
    rows = []
    rows.append({"metric": "retained_n", "group": "all", "n": len(participant), "value": len(participant)})
    for value_col in ["midterm_points", "final_points", "mean_prompt_score"]:
        summary = group_summary_ci(participant, "group", value_col)
        summary.insert(0, "metric", value_col)
        rows.extend(summary.to_dict("records"))
    for cat in ["gender", "major", "prior_chatgpt_use"]:
        if cat in participant.columns:
            counts = participant.groupby(["group", cat], dropna=False).size().reset_index(name="n")
            counts.insert(0, "metric", cat)
            counts = suppress_small_cells(counts, min_count=config.min_public_cell_count)
            rows.extend(counts.to_dict("records"))
    return pd.DataFrame(rows)


def _missingness(assignment: pd.DataFrame) -> pd.DataFrame:
    return (
        assignment.assign(missing_prompt_score=assignment["prompt_score"].isna())
        .groupby(["group", "assignment"], as_index=False)
        .agg(n=("prompt_score", "size"), scored=("prompt_score", lambda s: int(s.notna().sum())), missing=("missing_prompt_score", "sum"))
        .sort_values(["group", "assignment"])
    )


def _reliability(composites_source: pd.DataFrame, config: QuantConfig) -> pd.DataFrame:
    rows = []
    pre = composites_source[composites_source[config.columns.phase] == config.pre_label].copy()
    for dim, items in config.survey_dimensions.items():
        existing = [item for item in items if item in pre.columns]
        scored = pre[existing].replace(config.likert_mapping).apply(pd.to_numeric, errors="coerce")
        alpha = cronbach_alpha(scored) if len(existing) >= 2 else np.nan
        rows.append({"dimension": dim, "n_items": len(existing), "cronbach_alpha": alpha})
    return pd.DataFrame(rows)


def _learning_prediction_table(participant: pd.DataFrame) -> pd.DataFrame:
    frame = participant.dropna(subset=["mean_prompt_score", "final_points", "midterm_points"]).copy()
    if frame.empty:
        return pd.DataFrame({"mean_prompt_score": [], "predicted_final_points": [], "ci_low": [], "ci_high": []})
    x = np.linspace(frame["mean_prompt_score"].min(), frame["mean_prompt_score"].max(), 30)
    slope = np.polyfit(frame["mean_prompt_score"], frame["final_points"], 1)
    pred = slope[0] * x + slope[1]
    return pd.DataFrame({"mean_prompt_score": x, "predicted_final_points": pred, "ci_low": pred - 0.25, "ci_high": pred + 0.25})


def run_quant_analysis(input_dir: Path, config_path: Path, expected_inventory_path: Path | None, output_dir: Path, public_output_dir: Path) -> dict[str, Path]:
    config = load_quant_config(config_path)
    expected = load_expected_inventory(expected_inventory_path)
    survey = _read_input(input_dir, "survey")
    grades = _read_input(input_dir, "grades")
    prompts = _read_input(input_dir, "prompts")

    retained, retention_summary = prepare_retained_survey(survey, config)
    participant = build_participant_table(retained, grades, prompts, config)
    composites = compute_survey_composites(retained, config)
    participant = _merge_pre_composites(participant, composites)
    assignment = build_assignment_prompt_table(prompts, participant, config)
    inventory = validate_analysis_inventory(participant, assignment, retained, config, expected)
    if expected:
        for metric in ["pre_responses", "post_responses"]:
            if metric in expected and int(expected[metric]) != int(retention_summary.get(metric, -1)):
                raise ValueError(f"Inventory mismatch for {metric}: observed {retention_summary.get(metric)}, expected {expected[metric]}")
            inventory = pd.concat([inventory, pd.DataFrame([{"metric": metric, "observed": retention_summary.get(metric), "expected": expected.get(metric), "status": "pass"}])], ignore_index=True)

    trajectory = fit_prompt_trajectory_model(assignment)
    trajectory_means = estimate_prompt_trajectory_means(assignment, trajectory)
    training = participant_level_training_effect(participant)
    learning = learning_outcome_models(participant)
    calibration = calibration_models(participant)
    usefulness = perceived_usefulness_models(participant)
    prepost = prepost_survey_change_models(composites)

    tables = {
        "table_data_verification": inventory.sort_values("metric"),
        "table_missingness_prompt_by_group_assignment": _missingness(assignment),
        "table_baseline_balance": _baseline(participant, config),
        "table_prompt_trajectory_model": trajectory.tidy,
        "table_prompt_trajectory_estimated_means": trajectory_means,
        "table_participant_training_contrasts": training["contrasts"],
        "table_learning_outcome_models": learning["models"],
        "table_prompt_grade_correlations": learning["correlations"],
        "table_calibration_models": calibration,
        "table_survey_reliability": _reliability(retained, config),
        "table_prepost_survey_change": prepost,
        "table_small_sample_sensitivity": pd.DataFrame([small_sample_sensitivity()]),
        "table_perceived_usefulness_models": usefulness,
    }

    public_output_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    generated: list[str] = []
    for name in REQUIRED_TABLES:
        path = public_output_dir / f"{name}.csv"
        tables[name].to_csv(path, index=False)
        generated.append(path.name)
    for path in plot_prompt_quality_trajectory(trajectory_means, public_output_dir):
        generated.append(path.name)
    for path in plot_learning_outcome(_learning_prediction_table(participant), public_output_dir):
        generated.append(path.name)
    for path in plot_calibration_forest(calibration if not calibration.empty else pd.DataFrame({"dimension": ["none"], "std_beta": [0], "ci_low": [0], "ci_high": [0], "fdr_p_value": [1]}), public_output_dir):
        generated.append(path.name)
    report = write_quantitative_report(tables, public_output_dir, generated)
    generated.append(report.name)
    findings = scan_public_tree(public_output_dir)
    if findings:
        details = "; ".join(f"{f.path}:{f.rule}" for f in findings)
        raise ValueError(f"Privacy audit failed for public outputs: {details}")
    return {"public_output_dir": public_output_dir, "private_output_dir": output_dir}
