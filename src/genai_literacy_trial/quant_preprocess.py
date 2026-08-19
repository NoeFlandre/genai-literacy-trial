from __future__ import annotations

import hashlib
import math
import re
from typing import Mapping

import pandas as pd

from genai_literacy_trial.quant_config import ExpectedInventory, QuantConfig
from genai_literacy_trial.quant_schema import NORMALIZED_POST_LABEL, NORMALIZED_PRE_LABEL, PARTICIPANT_KEY_COLUMN

TRANSCRIPT_RE = re.compile(r"(^user\d+|^gpt\d+|/ user \d+|/ gpt\d+)", re.IGNORECASE)
EXPECTED_GROUP_COUNTS_KEY = "group_counts"
GROUP_COUNT_METRIC_PREFIX = "group_count_"


def participant_key(value: object) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:12]


def prepare_retained_survey(survey: pd.DataFrame, config: QuantConfig) -> tuple[pd.DataFrame, dict[str, int]]:
    c = config.columns
    df = survey.copy()
    df[PARTICIPANT_KEY_COLUMN] = df[c.id].map(participant_key)
    pre_keys = set(df.loc[df[c.phase] == config.pre_label, PARTICIPANT_KEY_COLUMN])
    post_keys = set(df.loc[df[c.phase] == config.post_label, PARTICIPANT_KEY_COLUMN])
    retained = pre_keys & post_keys
    out = df[df[PARTICIPANT_KEY_COLUMN].isin(retained)].copy()
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


def map_configured_numeric(series: pd.Series, mapping: Mapping[str, float]) -> pd.Series:
    return pd.to_numeric(series.replace(mapping), errors="coerce")


def _map_configured_scalar(value: object, mapping: Mapping[str, float]) -> float | None:
    raw = "" if pd.isna(value) else value
    mapped = mapping.get(str(raw))
    if mapped is not None:
        return mapped
    numeric = pd.to_numeric(pd.Series([raw]), errors="coerce").iloc[0]
    return None if pd.isna(numeric) else float(numeric)


def _conflicting_grade_fields(part: pd.DataFrame, key_columns: list[str]) -> list[str]:
    conflicting_fields = []
    for column in key_columns:
        values = [value for value in part[column].dropna().unique() if not pd.isna(value)]
        if len(values) > 1:
            conflicting_fields.append(f"{column}: {sorted(map(str, set(values)))}")
    return conflicting_fields


def _validate_grade_key_consistency(grade_df: pd.DataFrame, participant_key_col: str, key_columns: list[str]) -> None:
    conflicts = []
    for key, part in grade_df.groupby(participant_key_col, dropna=False):
        conflicting_fields = _conflicting_grade_fields(part, key_columns)
        if conflicting_fields:
            conflicts.append(f"{key} -> {', '.join(conflicting_fields)}")

    if conflicts:
        joined = "; ".join(conflicts)
        raise ValueError(f"Conflicting grade rows for participant_key in: {joined}")


def _validate_prompt_assignment_uniqueness(prompts: pd.DataFrame, config: QuantConfig) -> None:
    c = config.columns
    if c.id not in prompts.columns or c.assignment not in prompts.columns:
        return
    prompt_keys = prompts[[c.id, c.assignment]].copy()
    prompt_keys[PARTICIPANT_KEY_COLUMN] = prompt_keys[c.id].map(participant_key)
    duplicated = prompt_keys.duplicated([PARTICIPANT_KEY_COLUMN, c.assignment], keep=False)
    if not duplicated.any():
        return
    examples = (
        prompt_keys.loc[duplicated, [PARTICIPANT_KEY_COLUMN, c.assignment]]
        .drop_duplicates()
        .head(3)
    )
    sample = "; ".join(
        f"{row[PARTICIPANT_KEY_COLUMN]} assignment {row[c.assignment]}"
        for _, row in examples.iterrows()
    )
    raise ValueError(f"Duplicate prompt rows for participant assignment: {sample}")


def _prepare_grade_rows(
    survey: pd.DataFrame, grades: pd.DataFrame, config: QuantConfig
) -> tuple[pd.DataFrame, list[str], list[str]]:
    c = config.columns
    grade_df = grades.copy()
    grade_df[PARTICIPANT_KEY_COLUMN] = grade_df[c.id].map(participant_key)
    retained_keys = set(survey[PARTICIPANT_KEY_COLUMN]) if PARTICIPANT_KEY_COLUMN in survey.columns else set(survey[c.id].map(participant_key))
    grade_df = grade_df[grade_df[PARTICIPANT_KEY_COLUMN].isin(retained_keys)].copy()
    _validate_grade_key_consistency(grade_df, PARTICIPANT_KEY_COLUMN, [c.group, c.midterm_grade, c.final_grade])
    grade_df = grade_df.drop_duplicates(PARTICIPANT_KEY_COLUMN).copy()
    required = [PARTICIPANT_KEY_COLUMN, c.group, c.midterm_grade, c.final_grade]
    optional = [c.prior_chatgpt_use, c.gender, c.major]
    return grade_df, required, optional


def _prior_survey_rows(survey: pd.DataFrame, config: QuantConfig) -> pd.DataFrame:
    c = config.columns
    prior = survey[survey[c.phase] == config.pre_label].copy()
    prior[PARTICIPANT_KEY_COLUMN] = prior[c.id].map(participant_key)
    return prior


def _merge_participant_metadata(
    grade_df: pd.DataFrame,
    prior: pd.DataFrame,
    required: list[str],
    optional: list[str],
) -> pd.DataFrame:
    prior_cols = [PARTICIPANT_KEY_COLUMN] + _present_optional_columns(prior, optional)
    grade_columns = required + _present_optional_columns(grade_df, optional)
    participant = grade_df[grade_columns].merge(
        prior[prior_cols],
        on=PARTICIPANT_KEY_COLUMN,
        how="left",
        suffixes=("", "_survey"),
    )
    for col in optional:
        participant = _merge_optional_column(participant, col)
    return participant


def _present_optional_columns(frame: pd.DataFrame, optional: list[str]) -> list[str]:
    return [column for column in optional if column in frame.columns]


def _merge_optional_column(participant: pd.DataFrame, column: str) -> pd.DataFrame:
    survey_column = f"{column}_survey"
    if survey_column not in participant.columns:
        return participant
    out = participant.copy()
    if column not in out.columns:
        out[column] = out[survey_column]
    else:
        out[column] = out[column].combine_first(out[survey_column])
    return out.drop(columns=[survey_column])


def _prompt_summary(prompts: pd.DataFrame, config: QuantConfig) -> pd.DataFrame:
    c = config.columns
    return (
        prompts[[c.id, c.prompt_score]]
        .assign(**{PARTICIPANT_KEY_COLUMN: lambda d: d[c.id].map(participant_key)})
        .dropna(subset=[c.prompt_score])
        .groupby(PARTICIPANT_KEY_COLUMN, as_index=False)[c.prompt_score]
        .agg(mean_prompt_score="mean", scored_assignments="size")
    )


def build_participant_table(survey: pd.DataFrame, grades: pd.DataFrame, prompts: pd.DataFrame, config: QuantConfig) -> pd.DataFrame:
    c = config.columns
    _validate_prompt_assignment_uniqueness(prompts, config)
    grade_df, required, optional = _prepare_grade_rows(survey, grades, config)
    participant = _merge_participant_metadata(grade_df, _prior_survey_rows(survey, config), required, optional)
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
    participant = participant.merge(_prompt_summary(prompts, config), on=PARTICIPANT_KEY_COLUMN, how="left")
    keep = [col for col in [PARTICIPANT_KEY_COLUMN, "group", "prior_chatgpt_use", "gender", "major", "midterm_points", "final_points", "mean_prompt_score", "scored_assignments"] if col in participant.columns]
    return participant[keep].copy()


def build_assignment_prompt_table(prompts: pd.DataFrame, grades_or_participants: pd.DataFrame, config: QuantConfig) -> pd.DataFrame:
    c = config.columns
    _validate_prompt_assignment_uniqueness(prompts, config)
    transcript_cols = [col for col in prompts.columns if TRANSCRIPT_RE.search(str(col))]
    df = prompts.drop(columns=transcript_cols).copy()
    df[PARTICIPANT_KEY_COLUMN] = df[c.id].map(participant_key)
    df = df.rename(columns={c.assignment: "assignment", c.prompt_score: "prompt_score"})
    participants_source = grades_or_participants.copy()
    if "group" not in participants_source.columns and "group_x" in participants_source.columns:
        participants_source = participants_source.rename(columns={"group_x": "group"})
    participants = participants_source[[PARTICIPANT_KEY_COLUMN, "group"]].drop_duplicates()
    out = df[[PARTICIPANT_KEY_COLUMN, "assignment", "prompt_score"]].merge(participants, on=PARTICIPANT_KEY_COLUMN, how="inner")
    return out[[PARTICIPANT_KEY_COLUMN, "group", "assignment", "prompt_score"]].copy()


def _likert(frame: pd.DataFrame, columns: list[str], config: QuantConfig) -> pd.DataFrame:
    return frame[columns].apply(map_configured_numeric, mapping=config.likert_mapping)


def _dimension_composite(rows: pd.DataFrame, dimension: str, items: list[str], config: QuantConfig) -> dict[str, object]:
    existing = _existing_dimension_items(rows, items)
    if not existing:
        return {dimension: math.nan, f"{dimension}_items_present": 0}
    scored = _likert(rows, existing, config)
    scored = _reverse_code_dimension(scored, dimension, config)
    present = scored.notna().sum(axis=1)
    needed = max(1, math.ceil(len(existing) * 0.5))
    return {dimension: scored.mean(axis=1).where(present >= needed), f"{dimension}_items_present": present}


def _existing_dimension_items(rows: pd.DataFrame, items: list[str]) -> list[str]:
    return [item for item in items if item in rows.columns]


def _reverse_code_dimension(scored: pd.DataFrame, dimension: str, config: QuantConfig) -> pd.DataFrame:
    out = scored.copy()
    for item in config.reverse_coded_items.get(dimension, []):
        if item in out.columns:
            out[item] = 6 - out[item]
    return out


def compute_survey_composites(retained_survey: pd.DataFrame, config: QuantConfig) -> pd.DataFrame:
    c = config.columns
    rows = retained_survey.copy()
    rows[PARTICIPANT_KEY_COLUMN] = rows[c.id].map(participant_key)
    base_cols = [PARTICIPANT_KEY_COLUMN, c.phase]
    if c.group in rows.columns:
        base_cols.append(c.group)
    out = rows[base_cols].rename(columns={c.phase: "phase", c.group: "group"}).copy()
    out["phase"] = out["phase"].replace({config.pre_label: NORMALIZED_PRE_LABEL, config.post_label: NORMALIZED_POST_LABEL})
    for dimension, items in config.survey_dimensions.items():
        for column, values in _dimension_composite(rows, dimension, items, config).items():
            out[column] = values
    prior = c.prior_chatgpt_use
    if prior in rows.columns:
        out["prior_chatgpt_use_score"] = map_configured_numeric(rows[prior], config.likert_mapping)
    return out


def _prior_use_row(category: object, part: pd.DataFrame, config: QuantConfig, min_count: int | None) -> dict[str, object]:
    raw = category if not pd.isna(category) else ""
    mapped = _map_configured_scalar(raw, config.likert_mapping)
    count: int | str = int(len(part))
    if min_count is not None and count < min_count:
        count = "suppressed"
    return {
        "prior_chatgpt_use": str(raw),
        "n": count,
        "mapped_score": mapped,
        "mapped_status": "mapped" if mapped is not None else "unmapped",
    }


def prior_use_mapping_table(retained_survey: pd.DataFrame, config: QuantConfig, min_count: int | None = None) -> pd.DataFrame:
    c = config.columns
    if c.prior_chatgpt_use not in retained_survey.columns:
        return pd.DataFrame(columns=["prior_chatgpt_use", "n", "mapped_score", "mapped_status"])
    pre = retained_survey[retained_survey[c.phase] == config.pre_label].copy()
    return pd.DataFrame([_prior_use_row(category, part, config, min_count) for category, part in pre.groupby(c.prior_chatgpt_use, dropna=False, sort=True)])


def _validate_phase_inventory(retained_survey: pd.DataFrame, config: QuantConfig) -> None:
    phase_table = retained_survey.pivot_table(
        index=PARTICIPANT_KEY_COLUMN,
        columns=config.columns.phase,
        values=config.columns.id,
        aggfunc="size",
        fill_value=0,
    )
    if config.pre_label not in phase_table.columns or config.post_label not in phase_table.columns:
        raise ValueError("retained survey participants must have exactly one pre and one post row")
    if not ((phase_table[config.pre_label] == 1) & (phase_table[config.post_label] == 1)).all():
        raise ValueError("retained survey participants must have exactly one pre and one post row")


def _validate_participant_keys(participant: pd.DataFrame) -> None:
    if participant[PARTICIPANT_KEY_COLUMN].duplicated().any():
        raise ValueError("participant-level table contains duplicated participant_key")


def _validate_group_labels(participant: pd.DataFrame, config: QuantConfig) -> None:
    if not set(participant["group"].dropna()).issubset(set(config.groups)):
        raise ValueError("Invalid group labels outside configured groups")


def _validate_assignment_labels(assignment: pd.DataFrame, config: QuantConfig) -> None:
    if not set(assignment["assignment"].dropna().astype(int)).issubset(set(config.assignments)):
        raise ValueError("Invalid assignment values outside configured assignments")


def _validate_prompt_scores(assignment: pd.DataFrame) -> None:
    scores = assignment["prompt_score"].dropna()
    if not scores.between(1, 5).all():
        raise ValueError("Invalid prompt score outside 1-5")


def _validate_no_transcripts(assignment: pd.DataFrame) -> None:
    if any(TRANSCRIPT_RE.search(str(col)) for col in assignment.columns):
        raise ValueError("prompt table contains transcript columns after preprocessing")


def _validate_analysis_inputs(participant: pd.DataFrame, assignment: pd.DataFrame, config: QuantConfig) -> None:
    _validate_participant_keys(participant)
    _validate_group_labels(participant, config)
    _validate_assignment_labels(assignment, config)
    _validate_prompt_scores(assignment)
    _validate_no_transcripts(assignment)


def _observed_inventory(participant: pd.DataFrame, assignment: pd.DataFrame, retained_survey: pd.DataFrame) -> dict[str, int]:
    observed = {
        "retained_participants": int(len(participant)),
        "retained_survey_rows": int(len(retained_survey)),
        "prompt_assignment_rows": int(len(assignment)),
        "scored_prompt_observations": int(assignment["prompt_score"].notna().sum()),
        "missing_prompt_scores": int(assignment["prompt_score"].isna().sum()),
    }
    for group, count in participant["group"].value_counts().sort_index().items():
        observed[f"{GROUP_COUNT_METRIC_PREFIX}{group}"] = int(count)
    return observed


def _expected_inventory_value(metric: str, expected: ExpectedInventory | None) -> int | None:
    if not expected:
        return None
    direct = expected.get(metric)
    if direct is not None:
        return direct
    if metric.startswith(GROUP_COUNT_METRIC_PREFIX):
        return expected.get(EXPECTED_GROUP_COUNTS_KEY, {}).get(metric.removeprefix(GROUP_COUNT_METRIC_PREFIX))
    return None


def _inventory_row(metric: str, value: int, expected: ExpectedInventory | None) -> dict[str, object]:
    exp = _expected_inventory_value(metric, expected)
    status = "pass" if exp is None or int(exp) == value else "fail"
    if status == "fail":
        raise ValueError(f"Inventory mismatch for {metric}: observed {value}, expected {exp}")
    return {"metric": metric, "observed": value, "expected": exp, "status": status}


def _inventory_rows(observed: dict[str, int], expected: ExpectedInventory | None) -> list[dict[str, object]]:
    return [_inventory_row(metric, value, expected) for metric, value in observed.items()]


def validate_analysis_inventory(participant: pd.DataFrame, assignment: pd.DataFrame, retained_survey: pd.DataFrame, config: QuantConfig, expected: ExpectedInventory | None = None) -> pd.DataFrame:
    _validate_phase_inventory(retained_survey, config)
    _validate_analysis_inputs(participant, assignment, config)
    return pd.DataFrame(_inventory_rows(_observed_inventory(participant, assignment, retained_survey), expected))


def _suppression_category(table: pd.DataFrame, count_col: str, category_col: str | None) -> str | None:
    if category_col is not None:
        return category_col
    candidates = [col for col in table.columns if col not in {"metric", "group", count_col}]
    return candidates[-1] if candidates else None


def _suppression_groups(table: pd.DataFrame, mask: pd.Series, group_cols: list[str]):
    if group_cols:
        return table.loc[mask].groupby(group_cols, dropna=False, sort=True)
    return [((), table.loc[mask])]


def _suppressed_row(columns: pd.Index, category_col: str, count_col: str, group_cols: list[str], keys: object) -> dict[object, object]:
    row: dict[object, object] = {col: "" for col in columns}
    if group_cols:
        key_values = keys if isinstance(keys, tuple) else (keys,)
        for col, value in zip(group_cols, key_values, strict=True):
            row[col] = value
    row[category_col] = "Other/suppressed"
    row[count_col] = "suppressed"
    return row


def _collapsed_suppressed_rows(table: pd.DataFrame, mask: pd.Series, category_col: str, count_col: str) -> list[dict[object, object]]:
    group_cols = [col for col in ["metric", "group"] if col in table.columns]
    return [_suppressed_row(table.columns, category_col, count_col, group_cols, keys) for keys, _ in _suppression_groups(table, mask, group_cols)]


def suppress_small_cells(table: pd.DataFrame, count_col: str = "n", min_count: int = 5, category_col: str | None = None) -> pd.DataFrame:
    out = table.copy()
    if count_col not in out.columns:
        return out
    counts = pd.to_numeric(out[count_col], errors="coerce")
    mask = counts.fillna(0) < min_count
    category_col = _suppression_category(out, count_col, category_col)
    if category_col is None or not mask.any():
        return out
    safe = out.loc[~mask].copy()
    collapsed = _collapsed_suppressed_rows(out, mask, category_col, count_col)
    return pd.concat([safe, pd.DataFrame(collapsed)], ignore_index=True)
