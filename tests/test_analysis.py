from __future__ import annotations

import math

import pandas as pd

from genai_literacy_trial.analysis import (
    PAPER_TARGETS,
    anova_by_group,
    build_paper_aggregates,
    convert_letter_grade,
    filter_complete_pre_post,
    mean_prompt_scores,
    observed_metrics_from_outputs,
    optional_locus_control_before,
    pearson_stat,
    validate_against_targets,
)


def test_convert_letter_grade_uses_course_scale() -> None:
    assert convert_letter_grade("A") == 4.0
    assert convert_letter_grade("B+") == 3.3
    assert convert_letter_grade("C-") == 1.7
    assert convert_letter_grade("F") == 0.0
    assert math.isnan(convert_letter_grade(""))
    assert math.isnan(convert_letter_grade(None))


def test_filter_complete_pre_post_removes_dropout_emails() -> None:
    survey = pd.DataFrame(
        {
            "Email": ["p01", "p02", "p01"],
            "Phase": ["Before", "Before", "After"],
            "Score": [1, 2, 3],
        }
    )

    filtered, summary = filter_complete_pre_post(survey)

    assert filtered["Email"].tolist() == ["p01", "p01"]
    assert summary == {
        "students_before": 2,
        "students_after": 1,
        "dropouts": 1,
        "retained_students": 1,
    }


def test_mean_prompt_scores_aggregates_by_student_without_transcripts() -> None:
    prompts = pd.DataFrame(
        {
            "Email": ["p01", "p01", "p02"],
            "Assignment": [1, 2, 1],
            "Student prompting quality score (1 bad - 5 best)": [2, 4, 5],
            "User" + "1": ["raw prompt", "raw prompt", "raw prompt"],
            "GPT" + "1": ["raw answer", "raw answer", "raw answer"],
        }
    )

    scores = mean_prompt_scores(prompts)

    assert scores.to_dict(orient="records") == [
        {"Email": "p01", "mean_prompt_score": 3.0},
        {"Email": "p02", "mean_prompt_score": 5.0},
    ]
    assert "User" + "1" not in scores.columns
    assert "GPT" + "1" not in scores.columns


def test_statistical_helpers_return_named_results() -> None:
    frame = pd.DataFrame(
        {
            "group": ["A", "A", "B", "B", "C", "C"],
            "score": [1.0, 1.2, 2.0, 2.2, 4.0, 4.2],
            "grade": [1.1, 1.0, 2.1, 2.0, 4.1, 4.0],
        }
    )

    anova = anova_by_group(frame, value="score", group="group")
    corr = pearson_stat(frame["score"], frame["grade"])

    assert anova["statistic"] > 0
    assert anova["p_value"] < 0.05
    assert corr["correlation"] > 0.99
    assert corr["p_value"] < 0.001


def test_optional_locus_control_before_returns_empty_when_columns_are_unavailable() -> None:
    assert optional_locus_control_before(pd.DataFrame({"Phase": ["Before"]}), pd.DataFrame()) == {}
    assert optional_locus_control_before(pd.DataFrame({"Email": ["p01"]}), pd.DataFrame()) == {}


def test_optional_locus_control_before_uses_pre_rows_and_named_prompt_scores() -> None:
    survey = pd.DataFrame(
        {
            "Email": ["p01", "p02", "p03"],
            "Phase": ["Before", "Before", "After"],
            **{column: ["Agree", "Strongly agree", "Neutral"] for column in [
                " [I feel like I control what happens while working with ChatGPT because I use it as I want and get what I want]",
                " [When using ChatGPT, the primary responsibility to get what I want belongs to ChatGPT, not to me]",
                " [When using ChatGPT, I can retain attention and interest in this activity longer than when using other information search systems such as Google or Stack Overflow]",
                " [Time seems to pass quickly while I am using ChatGPT]",
            ]},
        }
    )
    prompt_scores = pd.DataFrame({"Email": ["p01", "p02"], "mean_prompt_score": [1.0, 2.0]})

    observed = optional_locus_control_before(survey, prompt_scores)

    assert observed["prompt_score_locus_control_before_n"] == 2.0
    assert observed["prompt_score_locus_control_before_r"] == 1.0


def test_observed_metrics_prefers_paper_statistics_and_falls_back_to_sample_summary() -> None:
    paper = pd.DataFrame({"metric": ["retained_students"], "observed": [45.0]})
    sample = pd.DataFrame({"retained_students": [44.0], "dropouts": [2.0]})

    assert observed_metrics_from_outputs({"paper_statistics": paper, "sample_summary": sample}) == {"retained_students": 45.0}
    assert observed_metrics_from_outputs({"sample_summary": sample}) == {"retained_students": 44.0, "dropouts": 2.0}


def test_build_paper_aggregates_uses_only_safe_aggregate_tables() -> None:
    survey = pd.DataFrame(
        {
            "Email": ["p01", "p02", "p03", "p01", "p02", "p03"],
            "Phase": ["Before", "Before", "Before", "After", "After", "After"],
        }
    )
    prompts = pd.DataFrame(
        {
            "Email": ["p01", "p02", "p03"],
            "Student prompting quality score (1 bad - 5 best)": [2.0, 3.0, 4.0],
            "User" + "1": ["secret", "secret", "secret"],
        }
    )
    grades = pd.DataFrame(
        {
            "Email": ["p01", "p02", "p03"],
            "Group": ["A", "B", "C"],
            "Midterm Grade": ["B", "B+", "A-"],
            "Final Grade": ["B+", "A-", "A"],
        }
    )

    outputs = build_paper_aggregates(survey=survey, prompts=prompts, grades=grades)

    assert set(outputs) == {
        "sample_summary",
        "prompt_training_means",
        "prompt_grade_correlations",
        "paper_statistics",
    }
    for table in outputs.values():
        assert "Email" not in table.columns
        assert "User" + "1" not in table.columns
    stats_table = outputs["paper_statistics"].set_index("metric")
    assert stats_table.loc["retained_students", "observed"] == 3
    assert stats_table.loc["prompt_score_grade_final_n", "observed"] == 3


def test_build_paper_aggregates_uses_shared_table_map_contract() -> None:
    assert build_paper_aggregates.__annotations__["return"] == "QuantTableMap"


def test_validate_against_targets_flags_mismatches_without_mutating_targets() -> None:
    observed = {
        "retained_students": 44,
        "prompt_training_anova_p": PAPER_TARGETS["prompt_training_anova_p"],
    }

    report = validate_against_targets(observed)

    assert report.loc[report["metric"] == "retained_students", "status"].item() == "mismatch"
    assert report.loc[report["metric"] == "prompt_training_anova_p", "status"].item() == "ok"
