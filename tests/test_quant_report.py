from __future__ import annotations

from pathlib import Path

import pandas as pd

from genai_literacy_trial.quant_pipeline import REQUIRED_TABLES
from genai_literacy_trial.quant_report import QUANTITATIVE_REPORT_FILENAME, REPORT_SECTION_TABLES, write_quantitative_report


def test_report_contains_required_sections_and_privacy_language(tmp_path: Path) -> None:
    tables = {
        "table_data_verification": pd.DataFrame({"metric": ["retained_participants"], "observed": [45], "expected": [45], "status": ["pass"]}),
        "table_prompt_grade_correlations": pd.DataFrame({"metric": ["mean_prompt_score vs final_points"], "n": [45], "correlation": [0.3], "p_value": [0.05]}),
        "table_learning_outcome_models": pd.DataFrame({"model": ["final_points"], "term": ["mean_prompt_score"], "n": [45]}),
        "table_survey_reliability": pd.DataFrame({"dimension": ["trust"], "cronbach_alpha": [0.5]}),
    }

    path = write_quantitative_report(tables, tmp_path, generated_files=["a.csv", "fig.pdf"])
    text = path.read_text(encoding="utf-8")

    for heading in [
        "Executive Summary",
        "Data Verification",
        "Unit-of-Analysis Audit",
        "Learning Outcomes",
        "Privacy Verification",
    ]:
        assert heading in text
    assert "old n=90 prompt-grade p-values are not used" in text
    assert "participant-level analyses use one row per participant" in text
    assert "Adjusted learning-outcome models" in text
    assert "Survey reliability" in text
    assert "@" not in text


def test_report_section_table_mapping_references_generated_tables() -> None:
    assert set(REPORT_SECTION_TABLES.values()).issubset(set(REQUIRED_TABLES))


def test_report_lists_itself_as_generated_file(tmp_path: Path) -> None:
    path = write_quantitative_report({}, tmp_path, generated_files=["a.csv"])
    text = path.read_text(encoding="utf-8")

    assert f"- `{QUANTITATIVE_REPORT_FILENAME}`" in text


def test_report_generated_file_list_is_deduplicated(tmp_path: Path) -> None:
    path = write_quantitative_report({}, tmp_path, generated_files=["a.csv", QUANTITATIVE_REPORT_FILENAME, "a.csv"])
    text = path.read_text(encoding="utf-8")

    assert text.count("- `a.csv`") == 1
    assert text.count(f"- `{QUANTITATIVE_REPORT_FILENAME}`") == 1
