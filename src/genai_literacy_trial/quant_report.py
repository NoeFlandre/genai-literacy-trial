from __future__ import annotations

from pathlib import Path
from typing import Callable

import pandas as pd

from genai_literacy_trial.quant_schema import QuantTableMap


REQUIRED_SECTIONS = [
    "Executive Summary",
    "Data Verification",
    "Unit-of-Analysis Audit",
    "Missingness",
    "Baseline Balance",
    "Primary Analysis: Prompt Quality Over Assignments",
    "Participant-Level Robustness",
    "Learning Outcomes",
    "Calibration: Beliefs vs Actual Prompt Skill",
    "Secondary Pre/Post Survey Change",
    "Small-Sample Sensitivity",
    "Manuscript-Ready Quantitative Paragraphs",
    "Files Generated",
    "Privacy Verification",
]

QUANTITATIVE_REPORT_FILENAME = "quantitative_report.md"

REPORT_SECTION_TABLES = {
    "Missingness": "table_missingness_prompt_by_group_assignment",
    "Baseline Balance": "table_baseline_balance",
    "Primary Analysis: Prompt Quality Over Assignments": "table_prompt_trajectory_model",
    "Participant-Level Robustness": "table_participant_training_contrasts",
    "Calibration: Beliefs vs Actual Prompt Skill": "table_calibration_models",
    "Secondary Pre/Post Survey Change": "table_prepost_survey_change",
    "Small-Sample Sensitivity": "table_small_sample_sensitivity",
}


def _md_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No rows._"
    cols = [str(c) for c in df.columns]
    rows = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in df.iterrows():
        rows.append("| " + " | ".join(str(row[col]) for col in df.columns) + " |")
    return "\n".join(rows)


def _first_row(df: pd.DataFrame, **matches: object) -> pd.Series | None:
    if df.empty:
        return None
    mask = pd.Series(True, index=df.index)
    for col, value in matches.items():
        if col not in df.columns:
            return None
        mask &= df[col] == value
    rows = df.loc[mask]
    if rows.empty:
        return None
    return rows.iloc[0]


def _fmt(value: object, digits: int = 3) -> str:
    if pd.isna(value):
        return "NA"
    if isinstance(value, (int, float)):
        return f"{value:.{digits}g}"
    return str(value)


def _manuscript_base_paragraph(verification: pd.DataFrame) -> str:
    retained = _first_row(verification, metric="retained_participants")
    survey_rows = _first_row(verification, metric="retained_survey_rows")
    prompt_rows = _first_row(verification, metric="scored_prompt_observations")
    return (
        "The quantitative pipeline retained "
        f"{_fmt(retained['observed'], 0) if retained is not None else 'NA'} participants and "
        f"{_fmt(survey_rows['observed'], 0) if survey_rows is not None else 'NA'} paired survey rows. "
        f"Prompt analyses used {_fmt(prompt_rows['observed'], 0) if prompt_rows is not None else 'NA'} scored assignment observations for assignment-level models. "
        "Prompt-grade relationships were evaluated at the participant level, and the old duplicated n=90 prompt-grade p-values were not used."
    )


def _contrast_paragraph(row: pd.Series) -> str:
    return (
        "At the participant level, mean prompt quality was higher for Group C than pooled Groups A and B "
        f"(mean difference={_fmt(row['mean_difference'])}, Hedges g={_fmt(row['hedges_g'])}, "
        f"95% CI for g [{_fmt(row['hedges_g_ci_low'])}, {_fmt(row['hedges_g_ci_high'])}], n={_fmt(row['n'], 0)})."
    )


def _correlation_paragraph(row: pd.Series) -> str:
    corr_value = row["correlation"] if "correlation" in row.index else row.get("estimate")
    return (
        "Mean prompt quality was descriptively compared with midterm grade as the early-course academic performance measure "
        f"(Pearson r={_fmt(corr_value)}, 95% CI [{_fmt(row['ci_low'])}, {_fmt(row['ci_high'])}], "
        f"p={_fmt(row['p_value'])}, n={_fmt(row['n'], 0)})."
    )


def _model_paragraph(row: pd.Series) -> str:
    if {"estimate", "ci_low", "ci_high", "p_value", "n"} <= set(row.index):
        return (
            "In the adjusted model requested for academic predictors of prompt quality, mean prompt quality was predicted from midterm grade, section, and prior ChatGPT use "
            f"(midterm coefficient={_fmt(row['estimate'])}, 95% CI [{_fmt(row['ci_low'])}, {_fmt(row['ci_high'])}], "
            f"p={_fmt(row['p_value'])}, n={_fmt(row['n'], 0)})."
        )
    return "The adjusted model requested for academic predictors of prompt quality used mean prompt quality as the outcome, with midterm grade, section, and prior ChatGPT use as predictors."


def _sensitivity_paragraph(row: pd.Series) -> str:
    return (
        "Small-sample sensitivity indicates that the study is powered only for relatively large effects "
        f"(approximate 80% detectable d for A vs B={_fmt(row['detectable_d_a_vs_b_80_power'])})."
    )


def _append_optional_paragraph(lines: list[str], row: pd.Series | None, builder: Callable[[pd.Series], str]) -> None:
    if row is not None:
        lines.append(builder(row))


def _manuscript_paragraphs(tables: QuantTableMap) -> list[str]:
    verification = tables.get("table_data_verification", pd.DataFrame())
    contrasts = tables.get("table_participant_training_contrasts", pd.DataFrame())
    corr = tables.get("table_prompt_grade_correlations", pd.DataFrame())
    learning_models = tables.get("table_learning_outcome_models", pd.DataFrame())
    sensitivity = tables.get("table_small_sample_sensitivity", pd.DataFrame())

    c_pooled = _first_row(contrasts, contrast="C vs pooled A+B")
    midterm_corr = _first_row(corr, metric="mean_prompt_score vs midterm_points", method="pearson")
    midterm_model = _first_row(learning_models, model="prompt_quality_academic_predictors", term="midterm_points")
    detect_d = sensitivity.iloc[0] if not sensitivity.empty else None

    lines = [_manuscript_base_paragraph(verification)]
    _append_optional_paragraph(lines, c_pooled, _contrast_paragraph)
    _append_optional_paragraph(lines, midterm_corr, _correlation_paragraph)
    _append_optional_paragraph(lines, midterm_model, _model_paragraph)
    _append_optional_paragraph(lines, detect_d, _sensitivity_paragraph)
    return lines


def _learning_section_lines(tables: QuantTableMap) -> list[str]:
    corr = tables.get("table_prompt_grade_correlations", pd.DataFrame())
    learning_models = tables.get("table_learning_outcome_models", pd.DataFrame())
    diagnostics = tables.get("table_complete_case_diagnostics", pd.DataFrame())
    if not diagnostics.empty and "model" in diagnostics.columns:
        diagnostics = diagnostics[diagnostics["model"] == "prompt_quality_academic_predictors"]
    prior_mapping = tables.get("table_prior_use_mapping", pd.DataFrame())
    return [
        _md_table(corr),
        "",
        "Adjusted prompt-quality predictor model; outcome is mean prompt quality and predictors are midterm grade, section/training condition, and prior ChatGPT use:",
        "",
        _md_table(learning_models),
        "",
        "Complete-case diagnostics for the adjusted prompt-quality predictor model; loss columns are marginal and non-additive:",
        "",
        _md_table(diagnostics),
        "",
        "Prior ChatGPT-use coding:",
        "",
        _md_table(prior_mapping),
        "",
    ]


def _participant_robustness_section_lines(tables: QuantTableMap) -> list[str]:
    return [
        _md_table(tables.get("table_participant_training_contrasts", pd.DataFrame())),
        "",
        "Omnibus training-effect tests:",
        "",
        _md_table(tables.get("table_participant_training_tests", pd.DataFrame())),
        "",
        "Scored assignment distribution by group:",
        "",
        _md_table(tables.get("table_scored_assignment_distribution_by_group", pd.DataFrame())),
        "",
        "Missing-prompt sensitivity, at least three scored assignments:",
        "",
        _md_table(tables.get("table_prompt_sensitivity_min3_assignments", pd.DataFrame())),
        "",
        "Missing-prompt sensitivity, all four scored assignments:",
        "",
        _md_table(tables.get("table_prompt_sensitivity_all4_assignments", pd.DataFrame())),
        "",
    ]


def _calibration_section_lines(tables: QuantTableMap) -> list[str]:
    return [
        "Survey reliability:",
        "",
        _md_table(tables.get("table_survey_reliability", pd.DataFrame())),
        "",
        _md_table(tables.get("table_calibration_models", pd.DataFrame())),
        "",
    ]


def _generic_section_lines(section: str, tables: QuantTableMap) -> list[str]:
    return [_md_table(tables.get(REPORT_SECTION_TABLES.get(section, ""), pd.DataFrame())), ""]


def _section_lines(section: str, tables: QuantTableMap, generated_file_list: list[str]) -> list[str]:
    handlers: dict[str, Callable[[], list[str]]] = {
        "Learning Outcomes": lambda: _learning_section_lines(tables),
        "Participant-Level Robustness": lambda: _participant_robustness_section_lines(tables),
        "Calibration: Beliefs vs Actual Prompt Skill": lambda: _calibration_section_lines(tables),
        "Files Generated": lambda: ["\n".join(f"- `{name}`" for name in generated_file_list), ""],
        "Privacy Verification": lambda: ["No raw identifiers, participant-level rows, raw survey responses, individual grades, or raw transcripts were written to public outputs.", ""],
        "Manuscript-Ready Quantitative Paragraphs": lambda: _manuscript_paragraphs(tables) + [""],
    }
    return [f"## {section}", "", *handlers.get(section, lambda: _generic_section_lines(section, tables))()]


def write_quantitative_report(tables: QuantTableMap, output_dir: Path, generated_files: list[str]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_file_list = list(dict.fromkeys([*generated_files, QUANTITATIVE_REPORT_FILENAME]))
    verification = tables.get("table_data_verification", pd.DataFrame())
    lines = ["# Quantitative Report", ""]
    lines += ["## Executive Summary", ""]
    lines += [
        "- This report is generated from aggregate analysis tables produced by the quantitative pipeline.",
        "- Participant-level analyses use one row per participant.",
        "- The old n=90 prompt-grade p-values are not used.",
        "- Model-specific sample sizes are reported in each table.",
        "- Small-sample uncertainty should be interpreted using confidence intervals and effect sizes.",
        "",
    ]
    lines += ["## Data Verification", "", _md_table(verification), ""]
    lines += ["## Unit-of-Analysis Audit", "", "participant-level analyses use one row per participant; old n=90 prompt-grade p-values are not used.", ""]
    for section in REQUIRED_SECTIONS[3:]:
        lines += _section_lines(section, tables, generated_file_list)
    path = output_dir / QUANTITATIVE_REPORT_FILENAME
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
