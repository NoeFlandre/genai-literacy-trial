from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable, cast

import numpy as np
import pandas as pd

from genai_literacy_trial.privacy import scan_public_tree
from genai_literacy_trial.quant_config import ExpectedInventory, QuantConfig, load_expected_inventory, load_quant_config
from genai_literacy_trial.quant_figures import FIGURE_FORMATS, plot_calibration_forest, plot_learning_outcome, plot_prompt_quality_trajectory
from genai_literacy_trial.quant_models import (
    calibration_models,
    complete_case_diagnostics,
    estimate_prompt_trajectory_means,
    fit_prompt_trajectory_model,
    learning_outcome_models,
    model_based_learning_prediction_table,
    participant_level_training_effect,
    perceived_usefulness_models,
    prompt_missingness_sensitivity,
    prepost_survey_change_models,
    ModelSummary,
)
from genai_literacy_trial.quant_preprocess import (
    build_assignment_prompt_table,
    build_participant_table,
    compute_survey_composites,
    map_configured_numeric,
    prior_use_mapping_table,
    prepare_retained_survey,
    suppress_small_cells,
    validate_analysis_inventory,
)
from genai_literacy_trial.quant_report import QUANTITATIVE_REPORT_FILENAME, write_quantitative_report
from genai_literacy_trial.quant_schema import (
    NORMALIZED_PRE_LABEL,
    PARTICIPANT_KEY_COLUMN,
    PRIVATE_OUTPUT_DIR_KEY,
    PUBLIC_OUTPUT_DIR_KEY,
    QUANT_TABLE_OUTPUT_FORMAT,
    REQUIRED_QUANT_TABLES,
    LearningOutcomeTables,
    PromptSensitivityTables,
    QuantPathMap,
    TrainingEffectTables,
)
from genai_literacy_trial.quant_stats import cronbach_alpha, group_summary_ci, small_sample_sensitivity


TABLE_OUTPUT_FORMAT = QUANT_TABLE_OUTPUT_FORMAT
INPUT_DATASETS = ("survey", "grades", "prompts")
INPUT_FILE_FORMATS = ("csv", "xlsx")
INPUT_READERS: dict[str, Callable[[Path], pd.DataFrame]] = {
    "csv": pd.read_csv,
    "xlsx": pd.read_excel,
}
COMPATIBILITY_INPUT_PREFIX = "public_cli_input_"
REQUIRED_TABLES = REQUIRED_QUANT_TABLES

GENERATED_PUBLIC_SUFFIXES = {
    f".{TABLE_OUTPUT_FORMAT}",
    *(f".{suffix}" for suffix in FIGURE_FORMATS),
    f".{QUANTITATIVE_REPORT_FILENAME.rsplit('.', maxsplit=1)[-1]}",
}
EMPTY_CALIBRATION_FOREST_ROW = {"dimension": "none", "std_beta": 0, "std_ci_low": 0, "std_ci_high": 0, "fdr_p_value": 1}
EMPTY_CALIBRATION_FOREST_COLUMNS = tuple(EMPTY_CALIBRATION_FOREST_ROW)


@dataclass(frozen=True)
class _PreparedAnalysis:
    config: QuantConfig
    expected: ExpectedInventory
    retained: pd.DataFrame
    retention_summary: dict[str, int]
    participant: pd.DataFrame
    composites: pd.DataFrame
    assignment: pd.DataFrame
    prior_mapping: pd.DataFrame
    inventory: pd.DataFrame


@dataclass(frozen=True)
class _FittedModels:
    trajectory: ModelSummary
    trajectory_means: pd.DataFrame
    training: TrainingEffectTables
    learning: LearningOutcomeTables
    calibration: pd.DataFrame
    usefulness: pd.DataFrame
    prepost: pd.DataFrame
    sensitivity: PromptSensitivityTables


def _input_candidates(input_dir: Path, name: str) -> list[tuple[Path, Callable[[Path], pd.DataFrame]]]:
    return [
        (input_dir / f"{name}.{suffix}", INPUT_READERS[suffix])
        for suffix in INPUT_FILE_FORMATS
        if suffix in INPUT_READERS and (input_dir / f"{name}.{suffix}").exists()
    ]


def _read_dataset(path: Path, name: str, reader: Callable[[Path], pd.DataFrame]) -> pd.DataFrame:
    try:
        return reader(path)
    except pd.errors.EmptyDataError as exc:
        raise ValueError(f"Input dataset {name} is empty: {path}") from exc


def _read_compatibility_dataset(path: Path, name: str) -> pd.DataFrame:
    return _read_dataset(path, name, pd.read_csv)


def _read_primary_input(candidates: list[tuple[Path, Callable[[Path], pd.DataFrame]]], name: str) -> pd.DataFrame | None:
    if len(candidates) > 1:
        names = ", ".join(path.name for path, _ in candidates)
        raise ValueError(f"Multiple input files found for {name}: {names}; keep exactly one primary input file")
    if not candidates:
        return None
    path, reader = candidates[0]
    return _read_dataset(path, name, reader)


def _read_input(input_dir: Path, name: str) -> pd.DataFrame:
    candidates = _input_candidates(input_dir, name)
    primary = _read_primary_input(candidates, name)
    if primary is not None:
        return primary
    # compatibility with clean_private_data CLI input names
    alt = input_dir / f"{COMPATIBILITY_INPUT_PREFIX}{name}.csv"
    if alt.exists():
        return _read_compatibility_dataset(alt, name)
    expected = " or ".join(f"{name}.{suffix}" for suffix in INPUT_FILE_FORMATS)
    raise FileNotFoundError(f"Missing {expected} in {input_dir}")


def _sample_bad_values(series: pd.Series, mask: pd.Series, limit: int = 3) -> str:
    values = [str(value) for value in series.loc[mask].dropna().unique()[:limit]]
    return ", ".join(values)


def _frame_input_issues(
    frames: dict[str, pd.DataFrame], required_columns: dict[str, tuple[str, ...]]
) -> tuple[list[str], set[str]]:
    issues: list[str] = []
    usable: set[str] = set()
    for name, frame in frames.items():
        frame_issues, is_usable = _frame_issue(name, frame, required_columns[name])
        issues.extend(frame_issues)
        if is_usable:
            usable.add(name)
    return issues, usable


def _frame_issue(name: str, frame: pd.DataFrame, required_columns: tuple[str, ...]) -> tuple[list[str], bool]:
    issues = [f"{name} is empty"] if frame.empty else []
    missing = [column for column in required_columns if column not in frame.columns]
    if missing:
        issues.append(f"{name} is missing required columns: {', '.join(missing)}")
        return issues, False
    return issues, True


def _numeric_input_issues(series: pd.Series, label: str, *, integer: bool = False) -> list[str]:
    numeric = pd.to_numeric(series, errors="coerce")
    issues: list[str] = []
    bad = series.notna() & numeric.isna()
    if bad.any():
        issues.append(f"prompts contains nonnumeric {label} values: {_sample_bad_values(series, bad)}")
    nonfinite = numeric.notna() & ~np.isfinite(numeric.astype(float))
    if nonfinite.any():
        issues.append(f"prompts contains nonfinite {label} values: {_sample_bad_values(series, nonfinite)}")
    noninteger = numeric.notna() & np.isfinite(numeric.astype(float)) & (numeric.astype(float) % 1 != 0)
    if integer and noninteger.any():
        issues.append(f"prompts contains noninteger {label} values: {_sample_bad_values(series, noninteger)}")
    return issues


def _prompt_input_issues(prompts: pd.DataFrame, config: QuantConfig) -> list[str]:
    c = config.columns
    return [
        *_numeric_input_issues(prompts[c.assignment], "assignment", integer=True),
        *_numeric_input_issues(prompts[c.prompt_score], "prompt_score"),
    ]


def _validate_quant_input_frames(survey: pd.DataFrame, grades: pd.DataFrame, prompts: pd.DataFrame, config: QuantConfig) -> None:
    c = config.columns
    required_columns = {
        "survey": (c.id, c.phase),
        "grades": (c.id, c.group, c.midterm_grade, c.final_grade),
        "prompts": (c.id, c.assignment, c.prompt_score),
    }
    frames = {"survey": survey, "grades": grades, "prompts": prompts}
    issues, usable = _frame_input_issues(frames, required_columns)
    if "prompts" in usable:
        issues.extend(_prompt_input_issues(prompts, config))

    if issues:
        raise ValueError("Invalid quantitative inputs: " + "; ".join(issues))


def _clean_public_output_dir(public_output_dir: Path) -> None:
    """Delete previous generated-style public outputs before writing a fresh run."""
    if not public_output_dir.exists():
        return
    for path in public_output_dir.iterdir():
        if path.is_file() and path.suffix.lower() in GENERATED_PUBLIC_SUFFIXES:
            path.unlink()


def _publish_staged_public_outputs(staging_dir: Path, public_output_dir: Path) -> None:
    public_output_dir.mkdir(parents=True, exist_ok=True)
    _clean_public_output_dir(public_output_dir)
    for path in staging_dir.iterdir():
        path.replace(public_output_dir / path.name)


def _merge_pre_composites(participant: pd.DataFrame, composites: pd.DataFrame) -> pd.DataFrame:
    pre = composites[composites["phase"] == NORMALIZED_PRE_LABEL].drop(columns=["phase"], errors="ignore")
    pre = pre.drop(columns=["group"], errors="ignore")
    pre = pre.drop_duplicates(PARTICIPANT_KEY_COLUMN)
    return participant.merge(pre, on=PARTICIPANT_KEY_COLUMN, how="left")


def _baseline(participant: pd.DataFrame, config: QuantConfig) -> pd.DataFrame:
    rows = []
    rows.append({"metric": "retained_n", "group": "all", "n": len(participant), "value": len(participant)})
    for value_col in ["midterm_points", "final_points", "mean_prompt_score"]:
        summary = group_summary_ci(participant, "group", value_col)
        summary.insert(0, "metric", value_col)
        rows.extend(summary.to_dict("records"))
    for cat in ["gender", "major", "prior_chatgpt_use"]:
        if cat in participant.columns:
            grouped_counts = cast(pd.Series, participant.groupby(["group", cat], dropna=False).size())
            counts = grouped_counts.reset_index(name="n")
            counts.insert(0, "metric", cat)
            counts = suppress_small_cells(counts, category_col=cat, min_count=config.min_public_cell_count)
            rows.extend(counts.to_dict("records"))
    return pd.DataFrame(rows)


def _missingness(assignment: pd.DataFrame) -> pd.DataFrame:
    return (
        assignment.assign(missing_prompt_score=assignment["prompt_score"].isna())
        .groupby(["group", "assignment"], as_index=False)
        .agg(n=("prompt_score", "size"), scored=("prompt_score", lambda s: int(s.notna().sum())), missing=("missing_prompt_score", "sum"))
        .sort_values(["group", "assignment"])
    )


def _calibration_forest_source(calibration: pd.DataFrame) -> pd.DataFrame:
    if not calibration.empty:
        return calibration
    return pd.DataFrame([EMPTY_CALIBRATION_FOREST_ROW], columns=EMPTY_CALIBRATION_FOREST_COLUMNS)


def _score_reliability_items(pre: pd.DataFrame, dimension: str, items: list[str], config: QuantConfig) -> tuple[list[str], pd.DataFrame]:
    existing = [item for item in items if item in pre.columns]
    scored = pre[existing].apply(map_configured_numeric, mapping=config.likert_mapping)
    for item in config.reverse_coded_items.get(dimension, []):
        if item in scored.columns:
            scored[item] = 6 - scored[item]
    return existing, scored


def _reliability_row(pre: pd.DataFrame, dimension: str, items: list[str], config: QuantConfig) -> dict[str, object]:
    existing, scored = _score_reliability_items(pre, dimension, items, config)
    alpha = cronbach_alpha(scored) if len(existing) >= 2 else np.nan
    return {"dimension": dimension, "n_items": len(existing), "cronbach_alpha": alpha}


def _reliability(composites_source: pd.DataFrame, config: QuantConfig) -> pd.DataFrame:
    pre = composites_source[composites_source[config.columns.phase] == config.pre_label].copy()
    return pd.DataFrame([_reliability_row(pre, dimension, items, config) for dimension, items in config.survey_dimensions.items()])


def _load_analysis_inputs(
    input_dir: Path, config_path: Path, expected_inventory_path: Path | None
) -> tuple[QuantConfig, ExpectedInventory, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    config = load_quant_config(config_path)
    expected = load_expected_inventory(expected_inventory_path)
    survey, grades, prompts = tuple(_read_input(input_dir, name) for name in INPUT_DATASETS)
    _validate_quant_input_frames(survey, grades, prompts, config)
    return config, expected, survey, grades, prompts


def _validate_prior_mapping(prior_mapping: pd.DataFrame) -> None:
    if prior_mapping.empty or not (prior_mapping["mapped_status"] == "unmapped").any():
        return
    unmapped = ", ".join(prior_mapping.loc[prior_mapping["mapped_status"] == "unmapped", "prior_chatgpt_use"].astype(str))
    raise ValueError(f"Unmapped prior ChatGPT use categories: {unmapped}")


def _append_expected_inventory(
    inventory: pd.DataFrame, expected: ExpectedInventory, retention_summary: dict[str, int]
) -> pd.DataFrame:
    if not expected:
        return inventory
    out = inventory
    for metric in ["pre_responses", "post_responses"]:
        if metric in expected and int(expected[metric]) != int(retention_summary.get(metric, -1)):
            raise ValueError(f"Inventory mismatch for {metric}: observed {retention_summary.get(metric)}, expected {expected[metric]}")
        out = pd.concat(
            [out, pd.DataFrame([{"metric": metric, "observed": retention_summary.get(metric), "expected": expected.get(metric), "status": "pass"}])],
            ignore_index=True,
        )
    return out


def _prepare_analysis(
    config: QuantConfig,
    expected: ExpectedInventory,
    survey: pd.DataFrame,
    grades: pd.DataFrame,
    prompts: pd.DataFrame,
) -> _PreparedAnalysis:
    retained, retention_summary = prepare_retained_survey(survey, config)
    participant = build_participant_table(retained, grades, prompts, config)
    composites = compute_survey_composites(retained, config)
    participant = _merge_pre_composites(participant, composites)
    assignment = build_assignment_prompt_table(prompts, participant, config)
    prior_mapping = prior_use_mapping_table(retained, config, min_count=config.min_public_cell_count)
    _validate_prior_mapping(prior_mapping)
    inventory = validate_analysis_inventory(participant, assignment, retained, config, expected)
    inventory = _append_expected_inventory(inventory, expected, retention_summary)
    return _PreparedAnalysis(config, expected, retained, retention_summary, participant, composites, assignment, prior_mapping, inventory)


def _fit_analysis_models(prepared: _PreparedAnalysis) -> _FittedModels:
    trajectory = fit_prompt_trajectory_model(prepared.assignment)
    return _FittedModels(
        trajectory=trajectory,
        trajectory_means=estimate_prompt_trajectory_means(prepared.assignment, trajectory),
        training=participant_level_training_effect(prepared.participant),
        learning=learning_outcome_models(prepared.participant),
        calibration=calibration_models(prepared.participant),
        usefulness=perceived_usefulness_models(prepared.participant),
        prepost=prepost_survey_change_models(prepared.composites),
        sensitivity=prompt_missingness_sensitivity(prepared.participant),
    )


def _build_analysis_tables(prepared: _PreparedAnalysis, models: _FittedModels) -> dict[str, pd.DataFrame]:
    return {
        "table_data_verification": prepared.inventory.sort_values("metric"),
        "table_missingness_prompt_by_group_assignment": _missingness(prepared.assignment),
        "table_baseline_balance": _baseline(prepared.participant, prepared.config),
        "table_prompt_trajectory_model": models.trajectory.tidy,
        "table_prompt_trajectory_estimated_means": models.trajectory_means,
        "table_participant_training_contrasts": models.training["contrasts"],
        "table_participant_training_tests": models.training["tests"],
        "table_learning_outcome_models": models.learning["models"],
        "table_prompt_grade_correlations": models.learning["correlations"],
        "table_calibration_models": models.calibration,
        "table_survey_reliability": _reliability(prepared.retained, prepared.config),
        "table_prepost_survey_change": models.prepost,
        "table_small_sample_sensitivity": pd.DataFrame([small_sample_sensitivity()]),
        "table_perceived_usefulness_models": models.usefulness,
        "table_complete_case_diagnostics": complete_case_diagnostics(prepared.participant),
        "table_prior_use_mapping": prepared.prior_mapping,
        "table_scored_assignment_distribution_by_group": models.sensitivity["scored_assignment_distribution"],
        "table_prompt_sensitivity_min3_assignments": models.sensitivity["min3_assignments"],
        "table_prompt_sensitivity_all4_assignments": models.sensitivity["all4_assignments"],
    }


def _write_tables(tables: dict[str, pd.DataFrame], staging_dir: Path) -> list[str]:
    generated: list[str] = []
    for name in REQUIRED_TABLES:
        path = staging_dir / f"{name}.{TABLE_OUTPUT_FORMAT}"
        tables[name].to_csv(path, index=False)
        generated.append(path.name)
    return generated


def _write_figures(tables: dict[str, pd.DataFrame], prepared: _PreparedAnalysis, models: _FittedModels, staging_dir: Path) -> list[str]:
    generated: list[str] = []
    for path in plot_prompt_quality_trajectory(models.trajectory_means, staging_dir):
        generated.append(path.name)
    for path in plot_learning_outcome(model_based_learning_prediction_table(prepared.participant), staging_dir):
        generated.append(path.name)
    for path in plot_calibration_forest(_calibration_forest_source(models.calibration), staging_dir):
        generated.append(path.name)
    return generated


def _publish_outputs(
    tables: dict[str, pd.DataFrame],
    prepared: _PreparedAnalysis,
    models: _FittedModels,
    output_dir: Path,
    public_output_dir: Path,
) -> None:
    public_output_dir.parent.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=f".{public_output_dir.name}.staging-", dir=public_output_dir.parent) as staging_path:
        staging_dir = Path(staging_path)
        generated = _write_tables(tables, staging_dir)
        generated.extend(_write_figures(tables, prepared, models, staging_dir))
        write_quantitative_report(tables, staging_dir, generated)
        findings = scan_public_tree(staging_dir)
        if findings:
            details = "; ".join(f"{finding.path}:{finding.rule}" for finding in findings)
            raise ValueError(f"Privacy audit failed for public outputs: {details}")
        _publish_staged_public_outputs(staging_dir, public_output_dir)


def run_quant_analysis(input_dir: Path, config_path: Path, expected_inventory_path: Path | None, output_dir: Path, public_output_dir: Path) -> QuantPathMap:
    config, expected, survey, grades, prompts = _load_analysis_inputs(input_dir, config_path, expected_inventory_path)
    prepared = _prepare_analysis(config, expected, survey, grades, prompts)
    models = _fit_analysis_models(prepared)
    tables = _build_analysis_tables(prepared, models)
    _publish_outputs(tables, prepared, models, output_dir, public_output_dir)
    return {PUBLIC_OUTPUT_DIR_KEY: public_output_dir, PRIVATE_OUTPUT_DIR_KEY: output_dir}
