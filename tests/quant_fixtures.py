from __future__ import annotations

from pathlib import Path

import pandas as pd

from genai_literacy_trial.quant_schema import NORMALIZED_POST_LABEL, NORMALIZED_PRE_LABEL


def synthetic_quant_frames() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    ids = [f"p{i:02d}" for i in range(1, 7)]
    groups = ["A", "A", "B", "B", "C", "C"]
    survey_rows = []
    for pid, group in zip(ids, groups, strict=True):
        phases = [NORMALIZED_PRE_LABEL, NORMALIZED_POST_LABEL] if pid != "p06" else [NORMALIZED_PRE_LABEL]
        for phase in phases:
            survey_rows.append(
                {
                    "participant_id": pid,
                    "phase": phase,
                    "group": group,
                    "prior_chatgpt_use": "low" if pid in {"p01", "p03", "p05"} else "high",
                    "useful_1": "Agree" if phase == NORMALIZED_PRE_LABEL else "Strongly agree",
                    "useful_2": "Neutral" if pid == "p02" else "Agree",
                    "control_1": "Agree",
                    "control_reverse": "Disagree",
                    "trust_1": "Agree",
                    "trust_2": "Agree",
                }
            )
    survey = pd.DataFrame(survey_rows)
    grades = pd.DataFrame(
        {
            "participant_id": ids,
            "group": groups,
            "midterm_grade": ["B", "B+", "B", "A-", "A-", "A"],
            "final_grade": ["B+", "B+", "A-", "A-", "A", "A"],
            "gender": ["X", "Y", "X", "Y", "X", "Y"],
            "major": ["M1", "M2", "M1", "M2", "M1", "M2"],
        }
    )
    prompt_rows = []
    for pid, group in zip(ids, groups, strict=True):
        for assignment in [1, 2, 3, 4]:
            score = None if pid == "p05" and assignment == 2 else min(5, assignment + (group == "C"))
            prompt_rows.append(
                {
                    "participant_id": pid,
                    "assignment": assignment,
                    "prompt_score": score,
                    "User" + "1": "raw prompt",
                    "GPT" + "1": "raw response",
                }
            )
    prompts = pd.DataFrame(prompt_rows)
    return survey, grades, prompts


def write_synthetic_quant_input(path: Path) -> None:
    survey, grades, prompts = synthetic_quant_frames()
    path.mkdir(parents=True, exist_ok=True)
    survey.to_csv(path / "survey.csv", index=False)
    grades.to_csv(path / "grades.csv", index=False)
    prompts.to_csv(path / "prompts.csv", index=False)
