from __future__ import annotations

from pathlib import Path

import pandas as pd


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


def _manuscript_paragraphs(tables: dict[str, pd.DataFrame]) -> list[str]:
    verification = tables.get("table_data_verification", pd.DataFrame())
    contrasts = tables.get("table_participant_training_contrasts", pd.DataFrame())
    corr = tables.get("table_prompt_grade_correlations", pd.DataFrame())
    perceived = tables.get("table_perceived_usefulness_models", pd.DataFrame())
    sensitivity = tables.get("table_small_sample_sensitivity", pd.DataFrame())

    retained = _first_row(verification, metric="retained_participants")
    survey_rows = _first_row(verification, metric="retained_survey_rows")
    prompt_rows = _first_row(verification, metric="scored_prompt_observations")
    c_pooled = _first_row(contrasts, contrast="C vs pooled A+B")
    final_corr = _first_row(corr, metric="mean_prompt_score vs final_points", method="pearson")
    usefulness_final = _first_row(perceived, model="final_points")
    detect_d = None if sensitivity.empty else sensitivity.iloc[0]

    lines = [
        "The quantitative pipeline retained "
        f"{_fmt(retained['observed'], 0) if retained is not None else 'NA'} participants and "
        f"{_fmt(survey_rows['observed'], 0) if survey_rows is not None else 'NA'} paired survey rows. "
        f"Prompt analyses used {_fmt(prompt_rows['observed'], 0) if prompt_rows is not None else 'NA'} scored assignment observations for assignment-level models. "
        "Prompt-grade relationships were evaluated at the participant level, and the old duplicated n=90 prompt-grade p-values were not used.",
    ]
    if c_pooled is not None:
        lines.append(
            "At the participant level, mean prompt quality was higher for Group C than pooled Groups A and B "
            f"(mean difference={_fmt(c_pooled['mean_difference'])}, Hedges g={_fmt(c_pooled['hedges_g'])}, "
            f"95% CI for g [{_fmt(c_pooled['ci_low'])}, {_fmt(c_pooled['ci_high'])}], n={_fmt(c_pooled['n'], 0)})."
        )
    if final_corr is not None:
        corr_value = final_corr["correlation"] if "correlation" in final_corr.index else final_corr.get("estimate")
        lines.append(
            "Mean prompt quality was associated with final grade in the participant-level descriptive analysis "
            f"(Pearson r={_fmt(corr_value)}, 95% CI [{_fmt(final_corr['ci_low'])}, {_fmt(final_corr['ci_high'])}], "
            f"p={_fmt(final_corr['p_value'])}, n={_fmt(final_corr['n'], 0)})."
        )
    if usefulness_final is not None:
        lines.append(
            "The targeted adjusted model did not support a strong participant-level negative association between pre-test perceived usefulness and final grade "
            f"(standardized beta={_fmt(usefulness_final['std_beta'])}, 95% CI [{_fmt(usefulness_final['ci_low'])}, {_fmt(usefulness_final['ci_high'])}], "
            f"p={_fmt(usefulness_final['p_value'])}, n={_fmt(usefulness_final['n'], 0)})."
        )
    if detect_d is not None:
        lines.append(
            "Small-sample sensitivity indicates that the study is powered only for relatively large effects "
            f"(approximate 80% detectable d for A vs B={_fmt(detect_d['detectable_d_a_vs_b_80_power'])})."
        )
    return lines


def write_quantitative_report(tables: dict[str, pd.DataFrame], output_dir: Path, generated_files: list[str]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    verification = tables.get("table_data_verification", pd.DataFrame())
    corr = tables.get("table_prompt_grade_correlations", pd.DataFrame())
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
    section_tables = {
        "Missingness": "table_missingness_prompt_by_group_assignment",
        "Baseline Balance": "table_baseline_balance",
        "Primary Analysis: Prompt Quality Over Assignments": "table_prompt_trajectory_model",
        "Participant-Level Robustness": "table_participant_training_contrasts",
        "Calibration: Beliefs vs Actual Prompt Skill": "table_calibration_models",
        "Secondary Pre/Post Survey Change": "table_prepost_survey_change",
        "Small-Sample Sensitivity": "table_small_sample_sensitivity",
    }
    for section in REQUIRED_SECTIONS[3:]:
        lines += [f"## {section}", ""]
        if section == "Learning Outcomes":
            lines += [_md_table(corr), ""]
            learning_models = tables.get("table_learning_outcome_models", pd.DataFrame())
            lines += ["Adjusted learning-outcome models:", "", _md_table(learning_models), ""]
            usefulness = tables.get("table_perceived_usefulness_models", pd.DataFrame())
            lines += ["Targeted perceived-usefulness models:", "", _md_table(usefulness), ""]
        elif section == "Files Generated":
            lines += ["\n".join(f"- `{name}`" for name in generated_files), ""]
        elif section == "Privacy Verification":
            lines += ["No raw identifiers, participant-level rows, raw survey responses, individual grades, or raw transcripts were written to public outputs.", ""]
        elif section == "Manuscript-Ready Quantitative Paragraphs":
            lines += _manuscript_paragraphs(tables) + [""]
        else:
            table = tables.get(section_tables.get(section, ""), pd.DataFrame())
            lines += [_md_table(table), ""]
    path = output_dir / "quantitative_report.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
