from __future__ import annotations

GRADE_POINTS: dict[str, float] = {
    "A": 4.0,
    "A-": 3.7,
    "B+": 3.3,
    "B": 3.0,
    "B-": 2.7,
    "C+": 2.3,
    "C": 2.0,
    "C-": 1.7,
    "D+": 1.3,
    "D": 1.0,
    "F": 0.0,
}

LIKERT_POINTS: dict[str, float] = {
    "Strongly disagree": 1.0,
    "Disagree": 2.0,
    "Neutral": 3.0,
    "Agree": 4.0,
    "Strongly agree": 5.0,
    "Highly unlikely": 1.0,
    "Unlikely": 2.0,
    "Likely": 4.0,
    "Highly likely": 5.0,
}
