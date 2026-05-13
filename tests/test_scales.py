from genai_literacy_trial.scales import GRADE_POINTS, LIKERT_POINTS


def test_shared_grade_and_likert_scales_keep_expected_values() -> None:
    assert GRADE_POINTS["A"] == 4.0
    assert GRADE_POINTS["A-"] == 3.7
    assert GRADE_POINTS["F"] == 0.0

    assert LIKERT_POINTS["Strongly disagree"] == 1.0
    assert LIKERT_POINTS["Neutral"] == 3.0
    assert LIKERT_POINTS["Strongly agree"] == 5.0
    assert LIKERT_POINTS["Highly unlikely"] == 1.0
    assert LIKERT_POINTS["Highly likely"] == 5.0
