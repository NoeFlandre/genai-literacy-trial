from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def _save(fig, output_dir: Path, stem: str) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = [output_dir / f"{stem}.pdf", output_dir / f"{stem}.png"]
    for path in paths:
        fig.savefig(path, bbox_inches="tight", dpi=300, metadata={"Creator": "genai-literacy-trial"})
    plt.close(fig)
    return paths


def plot_prompt_quality_trajectory(table: pd.DataFrame, output_dir: Path) -> list[Path]:
    fig, ax = plt.subplots(figsize=(4.8, 3.2))
    for group, part in table.groupby("group", sort=True):
        part = part.sort_values("assignment")
        ax.errorbar(part["assignment"], part["mean"], yerr=[part["mean"] - part["ci_low"], part["ci_high"] - part["mean"]], marker="o", label=str(group), linewidth=1.5)
    ax.set_xlabel("Assignment")
    ax.set_ylabel("Prompt quality")
    ax.set_ylim(1, 5)
    ax.legend(title="Group", frameon=False)
    ax.grid(alpha=0.2)
    return _save(fig, output_dir, "fig_prompt_quality_trajectory")


def plot_learning_outcome(table: pd.DataFrame, output_dir: Path) -> list[Path]:
    fig, ax = plt.subplots(figsize=(4.8, 3.2))
    ax.plot(table["mean_prompt_score"], table["predicted_final_points"], color="black")
    ax.fill_between(table["mean_prompt_score"], table["ci_low"], table["ci_high"], color="0.8")
    ax.set_xlabel("Mean prompt quality")
    ax.set_ylabel("Predicted final grade points")
    ax.grid(alpha=0.2)
    return _save(fig, output_dir, "fig_prompt_quality_learning_outcome")


def plot_calibration_forest(table: pd.DataFrame, output_dir: Path) -> list[Path]:
    fig, ax = plt.subplots(figsize=(5.2, max(3.2, 0.35 * len(table))))
    plot = table.sort_values("std_beta").reset_index(drop=True)
    y = range(len(plot))
    ax.errorbar(plot["std_beta"], y, xerr=[plot["std_beta"] - plot["ci_low"], plot["ci_high"] - plot["std_beta"]], fmt="o", color="black")
    ax.axvline(0, color="0.5", linewidth=1)
    ax.set_yticks(list(y), plot["dimension"])
    ax.set_xlabel("Standardized coefficient")
    ax.grid(axis="x", alpha=0.2)
    return _save(fig, output_dir, "fig_calibration_forest")
