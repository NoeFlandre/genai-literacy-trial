from __future__ import annotations

import hashlib
import math
import re
from typing import Any, Mapping

import pandas as pd

from genai_literacy_trial.quant_config import QuantConfig

TRANSCRIPT_RE = re.compile(r"(^user\d+|^gpt\d+|/ user \d+|/ gpt\d+)", re.IGNORECASE)


def participant_key(value: object) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:12]


def prepare_retained_survey(survey: pd.DataFrame, config: QuantConfig) -> tuple[pd.DataFrame, dict[str, int]]:
    c = config.columns
    df = survey.copy()
    df["participant_key"] = df[c.id].map(participant_key)
    pre_keys = set(df.loc[df[c.phase] == config.pre_label, "participant_key"])
    post_keys = set(df.loc[df[c.phase] == config.post_label, "participant_key"])
    retained = pre_keys & post_keys
    out = df[df["participant_key"].isin(retained)].copy()
    summary = {
        "pre_responses": int(len(pre_keys)),
        "post_responses": int(len(post_keys)),
        "dropouts": int(len(pre_keys - post_keys)),
        "retained_participants": int(len(retained)),
        "retained_survey_rows": int(len(out)),
    }
    return out, summary


def _map_grade(series: pd.Series, config: QuantConfig, column: str) -> pd.Series:
    mapped = series.map(config.grade_mapping)
    bad = sorted(set(series.dropna().astype(str)) - set(config.grade_mapping))
    if bad:
        raise ValueError(f"Unmapped letter grades in {column}: {bad}")
    return mapped


def _map_configured_numeric(series: pd.Series, mapping: Mapping[str, float]) -> pd.Series:
    return pd.to_numeric(series.replace(mapping), errors="coerce")


def _map_configured_scalar(value: object, mapping: Mapping[str, float]) -> float | None:
    raw = "" if pd.isna(value) else value
    mapped = mapping.get(str(raw))
    if mapped is not None:
        return mapped
    numeric = pd.to_numeric(pd.Series([raw]), errors="coerce").iloc[0]
    return None if pd.isna(numeric) else float(numeric)


def build_participant_table(survey: pd.DataFrame, grades: pd.DataFrame, prompts: pd.DataFrame, config: QuantConfig) -> pd.DataFrame:
    c = config.columns
    grade_df = grades.copy()
    grade_df["participant_key"] = grade_df[c.id].map(participant_key)
    retained_keys = set(survey["participant_key"]) if "participant_key" in survey.columns else set(survey[c.id].map(participant_key))
    grade_df = grade_df[grade_df["participant_key"].isin(retained_keys)].copy()
    grade_df = grade_df.drop_duplicates("participant_key").copy()
    required = ["participant_key", c.group, c.midterm_grade, c.final_grade]
    optional = [c.prior_chatgpt_use, c.gender, c.major]
    prior = survey[survey[c.phase] == config.pre_label].copy()
    prior["participant_key"] = prior[c.id].map(participant_key)
    prior_cols = ["participant_key"] + [col for col in optional if col in prior.columns]
    participant = grade_df[required + [col for col in optional if col in grade_df.columns]].merge(
        prior[prior_cols],
        on="participant_key",
        how="left",
        suffixes=("", "_survey"),
    )
    for col in optional:
        survey_col = f"{col}_survey"
        if survey_col in participant.columns:
            if col not in participant.columns:
                participant[col] = participant[survey_col]
            else:
                participant[col] = participant[col].combine_first(participant[survey_col])
            participant = participant.drop(columns=[survey_col])
    participant = participant.rename(
        columns={
            c.group: "group",
            c.midterm_grade: "midterm_grade",
            c.final_grade: "final_grade",
            c.prior_chatgpt_use: "prior_chatgpt_use",
            c.gender: "gender",
            c.major: "major",
        }
    )
    participant["midterm_points"] = _map_grade(participant["midterm_grade"], config, "midterm_grade")
    participant["final_points"] = _map_grade(participant["final_grade"], config, "final_grade")
    prompt_mean = (
        prompts[[c.id, c.prompt_score]]
        .assign(participant_key=lambda d: d[c.id].map(participant_key))
        .dropna(subset=[c.prompt_score])
        .groupby("participant_key", as_index=False)[c.prompt_score]
        .agg(mean_prompt_score="mean", scored_assignments="size")
    )
    participant = participant.merge(prompt_mean, on="participant_key", how="left")
    keep = [col for col in ["participant_key", "group", "prior_chatgpt_use", "gender", "major", "midterm_points", "final_points", "mean_prompt_score", "scored_assignments"] if col in participant.columns]
    return participant[keep].copy()


def build_assignment_prompt_table(prompts: pd.DataFrame, grades_or_participants: pd.DataFrame, config: QuantConfig) -> pd.DataFrame:
    c = config.columns
    transcript_cols = [col for col in prompts.columns if TRANSCRIPT_RE.search(str(col))]
    df = prompts.drop(columns=transcript_cols).copy()
    df["participant_key"] = df[c.id].map(participant_key)
    df = df.rename(columns={c.assignment: "assignment", c.prompt_score: "prompt_score"})
    participants_source = grades_or_participants.copy()
    if "group" not in participants_source.columns and "group_x" in participants_source.columns:
        participants_source = participants_source.rename(columns={"group_x": "group"})
    participants = participants_source[["participant_key", "group"]].drop_duplicates()
    out = df[["participant_key", "assignment", "prompt_score"]].merge(participants, on="participant_key", how="inner")
    return out[["participant_key", "group", "assignment", "prompt_score"]].copy()


def _likert(frame: pd.DataFrame, columns: list[str], config: QuantConfig) -> pd.DataFrame:
    return frame[columns].apply(_map_configured_numeric, mapping=config.likert_mapping)


def compute_survey_composites(retained_survey: pd.DataFrame, config: QuantConfig) -> pd.DataFrame:
    c = config.columns
    rows = retained_survey.copy()
    rows["participant_key"] = rows[c.id].map(participant_key)
    base_cols = ["participant_key", c.phase]
    if c.group in rows.columns:
        base_cols.append(c.group)
    out = rows[base_cols].rename(columns={c.phase: "phase", c.group: "group"}).copy()
    out["phase"] = out["phase"].replace({config.pre_label: "pre", config.post_label: "post"})
    for dimension, items in config.survey_dimensions.items():
        existing = [item for item in items if item in rows.columns]
        if not existing:
            out[dimension] = math.nan
            out[f"{dimension}_items_present"] = 0
            continue
        scored = _likert(rows, existing, config)
        for item in config.reverse_coded_items.get(dimension, []):
            if item in scored.columns:
                scored[item] = 6 - scored[item]
        present = scored.notna().sum(axis=1)
        needed = max(1, math.ceil(len(existing) * 0.5))
        out[dimension] = scored.mean(axis=1).where(present >= needed)
        out[f"{dimension}_items_present"] = present
    prior = c.prior_chatgpt_use
    if prior in rows.columns:
        out["prior_chatgpt_use_score"] = _map_configured_numeric(rows[prior], config.likert_mapping)
    return out


def prior_use_mapping_table(retained_survey: pd.DataFrame, config: QuantConfig, min_count: int | None = None) -> pd.DataFrame:
    c = config.columns
    if c.prior_chatgpt_use not in retained_survey.columns:
        return pd.DataFrame(columns=["prior_chatgpt_use", "n", "mapped_score", "mapped_status"])
    pre = retained_survey[retained_survey[c.phase] == config.pre_label].copy()
    rows = []
    for category, part in pre.groupby(c.prior_chatgpt_use, dropna=False, sort=True):
        raw = category if not pd.isna(category) else ""
        mapped = _map_configured_scalar(raw, config.likert_mapping)
        count: int | str = int(len(part))
        if min_count is not None and count < min_count:
            count = "suppressed"
        rows.append(
            {
                "prior_chatgpt_use": str(raw),
                "n": count,
                "mapped_score": mapped,
                "mapped_status": "mapped" if mapped is not None else "unmapped",
            }
        )
    return pd.DataFrame(rows)


def validate_analysis_inventory(participant: pd.DataFrame, assignment: pd.DataFrame, retained_survey: pd.DataFrame, config: QuantConfig, expected: dict[str, Any] | None = None) -> pd.DataFrame:
    phase_table = retained_survey.pivot_table(
        index="participant_key",
        columns=config.columns.phase,
        values=config.columns.id,
        aggfunc="size",
        fill_value=0,
    )
    if config.pre_label not in phase_table.columns or config.post_label not in phase_table.columns:
        raise ValueError("retained survey participants must have exactly one pre and one post row")
    if not ((phase_table[config.pre_label] == 1) & (phase_table[config.post_label] == 1)).all():
        raise ValueError("retained survey participants must have exactly one pre and one post row")
    if participant["participant_key"].duplicated().any():
        raise ValueError("participant-level table contains duplicated participant_key")
    if not set(participant["group"].dropna()).issubset(set(config.groups)):
        raise ValueError("Invalid group labels outside configured groups")
    if not set(assignment["assignment"].dropna().astype(int)).issubset(set(config.assignments)):
        raise ValueError("Invalid assignment values outside configured assignments")
    scores = assignment["prompt_score"].dropna()
    if not scores.between(1, 5).all():
        raise ValueError("Invalid prompt score outside 1-5")
    transcript_cols = [col for col in assignment.columns if TRANSCRIPT_RE.search(str(col))]
    if transcript_cols:
        raise ValueError("prompt table contains transcript columns after preprocessing")
    observed = {
        "retained_participants": int(len(participant)),
        "retained_survey_rows": int(len(retained_survey)),
        "prompt_assignment_rows": int(len(assignment)),
        "scored_prompt_observations": int(assignment["prompt_score"].notna().sum()),
        "missing_prompt_scores": int(assignment["prompt_score"].isna().sum()),
    }
    for group, count in participant["group"].value_counts().sort_index().items():
        observed[f"group_count_{group}"] = int(count)
    rows = []
    for metric, value in observed.items():
        exp = None if not expected else expected.get(metric)
        if exp is None and expected and metric.startswith("group_count_"):
            exp = expected.get("group_counts", {}).get(metric.removeprefix("group_count_"))
        status = "pass" if exp is None or int(exp) == value else "fail"
        if status == "fail":
            raise ValueError(f"Inventory mismatch for {metric}: observed {value}, expected {exp}")
        rows.append({"metric": metric, "observed": value, "expected": exp, "status": status})
    return pd.DataFrame(rows)


def suppress_small_cells(table: pd.DataFrame, count_col: str = "n", min_count: int = 5, category_col: str | None = None) -> pd.DataFrame:
    out = table.copy()
    if count_col not in out.columns:
        return out
    counts = pd.to_numeric(out[count_col], errors="coerce")
    mask = counts.fillna(0) < min_count
    if category_col is None:
        candidates = [col for col in out.columns if col not in {"metric", "group", count_col}]
        category_col = candidates[-1] if candidates else None
    if category_col is None or not mask.any():
        return out
    safe = out.loc[~mask].copy()
    collapsed = []
    group_cols = [col for col in ["metric", "group"] if col in out.columns]
    for keys, part in out.loc[mask].groupby(group_cols, dropna=False, sort=True) if group_cols else [((), out.loc[mask])]:
        row = {col: "" for col in out.columns}
        if group_cols:
            if not isinstance(keys, tuple):
                keys = (keys,)
            for col, value in zip(group_cols, keys, strict=True):
                row[col] = value
        row[category_col] = "Other/suppressed"
        row[count_col] = "suppressed"
        collapsed.append(row)
    return pd.concat([safe, pd.DataFrame(collapsed)], ignore_index=True)
