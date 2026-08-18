from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


PROMPT_TRAJECTORY_FIGURE = "fig_prompt_quality_trajectory"
LEARNING_OUTCOME_FIGURE = "fig_prompt_quality_learning_outcome"
CALIBRATION_FOREST_FIGURE = "fig_calibration_forest"
FIGURE_STEMS = (
    PROMPT_TRAJECTORY_FIGURE,
    LEARNING_OUTCOME_FIGURE,
    CALIBRATION_FOREST_FIGURE,
)
FIGURE_FORMATS = ("pdf", "png")


def _save(fig, output_dir: Path, stem: str) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = [output_dir / f"{stem}.{suffix}" for suffix in FIGURE_FORMATS]
    for path in paths:
        fig.savefig(path, bbox_inches="tight", dpi=300, metadata={"Creator": "genai-literacy-trial", "CreationDate": None})
    plt.close(fig)
    return paths


def plot_prompt_quality_trajectory(table: pd.DataFrame, output_dir: Path) -> list[Path]:
    fig, ax = plt.subplots(figsize=(4.8, 3.4))
    for group, part in table.groupby("group", sort=True):
        part = part.sort_values("assignment")
        ax.errorbar(part["assignment"], part["mean"], yerr=[part["mean"] - part["ci_low"], part["ci_high"] - part["mean"]], marker="o", label=str(group), linewidth=1.5)
    ax.set_xlabel("Assignment")
    ax.set_ylabel("Prompt quality")
    ax.set_ylim(1, 5)
    ax.legend(title="Group", loc="upper center", bbox_to_anchor=(0.5, 1.28), ncol=3, frameon=False, handlelength=1.8, columnspacing=1.2)
    ax.grid(alpha=0.2)
    return _save(fig, output_dir, PROMPT_TRAJECTORY_FIGURE)


def plot_learning_outcome(table: pd.DataFrame, output_dir: Path) -> list[Path]:
    fig, ax = plt.subplots(figsize=(4.8, 3.2))
    ax.plot(table["midterm_points"], table["predicted_mean_prompt_score"], color="black")
    ax.fill_between(table["midterm_points"], table["ci_low"], table["ci_high"], color="0.8")
    ax.set_xlabel("Midterm grade points")
    ax.set_ylabel("Predicted mean prompt quality")
    ax.grid(alpha=0.2)
    return _save(fig, output_dir, LEARNING_OUTCOME_FIGURE)


def plot_calibration_forest(table: pd.DataFrame, output_dir: Path) -> list[Path]:
    fig, ax = plt.subplots(figsize=(5.2, max(3.2, 0.35 * len(table))))
    plot = table.sort_values("std_beta").reset_index(drop=True)
    y = range(len(plot))
    ax.errorbar(plot["std_beta"], y, xerr=[plot["std_beta"] - plot["std_ci_low"], plot["std_ci_high"] - plot["std_beta"]], fmt="o", color="black")
    ax.axvline(0, color="0.5", linewidth=1)
    ax.set_yticks(list(y), plot["dimension"])
    ax.set_xlabel("Standardized coefficient")
    ax.grid(axis="x", alpha=0.2)
    return _save(fig, output_dir, CALIBRATION_FOREST_FIGURE)
