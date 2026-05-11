from __future__ import annotations

from pathlib import Path

import pandas as pd

from genai_literacy_trial.quant_report import write_quantitative_report


def test_report_contains_required_sections_and_privacy_language(tmp_path: Path) -> None:
    tables = {
        "table_data_verification": pd.DataFrame({"metric": ["retained_participants"], "observed": [45], "expected": [45], "status": ["pass"]}),
        "table_prompt_grade_correlations": pd.DataFrame({"metric": ["mean_prompt_score vs final_points"], "n": [45], "correlation": [0.3], "p_value": [0.05]}),
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
    assert "@" not in text

