#!/usr/bin/env python
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
import shlex
import subprocess


REPO_ROOT = Path(__file__).resolve().parents[1]
COVERAGE_JSON = Path("/tmp/genai-literacy-trial-coverage-gauntlet.json")
RADON_JSON = Path("/tmp/genai-literacy-trial-cc-gauntlet.json")


@dataclass(frozen=True)
class Command:
    argv: tuple[str, ...]
    stdout_path: Path | None = None


@dataclass(frozen=True)
class Stage:
    name: str
    commands: tuple[Command, ...]


def _uv_run(*args: str) -> tuple[str, ...]:
    return ("uv", "run", "--locked", "--no-sync", *args)


GAUNTLET_STAGES = (
    Stage(
        "baseline",
        (
            Command(("uv", "lock", "--check")),
            Command(("uv", "sync", "--locked", "--dev")),
        ),
    ),
    Stage("ruff", (Command(_uv_run("ruff", "check", ".")),)),
    Stage("ty", (Command(_uv_run("ty", "check", ".")),)),
    Stage(
        "tests",
        (
            Command(_uv_run("python", "-m", "coverage", "erase")),
            Command(_uv_run("python", "-m", "coverage", "run", "--source=src,scripts", "-m", "pytest")),
        ),
    ),
    Stage(
        "acceptance tests",
        (
            Command(
                _uv_run(
                    "pytest",
                    "tests/test_high_risk_contracts.py",
                    "tests/test_reproducibility_scripts.py",
                    "tests/test_validate_artifacts.py",
                    "-q",
                )
            ),
        ),
    ),
    Stage(
        "architecture checks",
        (
            Command(
                _uv_run(
                    "pytest",
                    "tests/test_architecture.py",
                    "tests/test_cli_imports.py",
                    "tests/test_docs.py",
                    "-q",
                )
            ),
            Command(_uv_run("mkdocs", "build", "--strict", "--site-dir", "/tmp/genai-literacy-trial-site-gauntlet")),
        ),
    ),
    Stage(
        "CRAP",
        (
            Command(_uv_run("python", "-m", "coverage", "json", "-o", str(COVERAGE_JSON))),
            Command(_uv_run("radon", "cc", "src", "scripts", "-j"), stdout_path=RADON_JSON),
            Command(
                _uv_run(
                    "python",
                    "scripts/check_crap.py",
                    "--coverage-json",
                    str(COVERAGE_JSON),
                    "--radon-json",
                    str(RADON_JSON),
                )
            ),
        ),
    ),
    Stage("mutation tests", (Command(_uv_run("python", "scripts/run_mutation_gate.py")),)),
    Stage(
        "smoke test",
        (
            Command(_uv_run("python", "scripts/reproduce_small.py")),
            Command(
                _uv_run(
                    "python",
                    "scripts/validate_artifacts.py",
                    "--mode",
                    "small",
                    "--public-output-dir",
                    "repro_outputs/small/public",
                )
            ),
            Command(_uv_run("genai-literacy-trial", "audit-privacy", "--root", "repro_outputs/small/public")),
            Command(_uv_run("python", "scripts/check_repo_hygiene.py")),
        ),
    ),
    Stage(
        "diff review",
        (
            Command(("git", "diff", "--check", "HEAD")),
            Command(("git", "diff", "--stat", "HEAD")),
            Command(("git", "status", "--short")),
        ),
    ),
)


def _run_command(command: Command) -> int:
    print(f"$ {shlex.join(command.argv)}")
    try:
        if command.stdout_path is None:
            completed = subprocess.run(command.argv, cwd=REPO_ROOT, check=False)
        else:
            with command.stdout_path.open("w", encoding="utf-8") as output:
                completed = subprocess.run(command.argv, cwd=REPO_ROOT, stdout=output, check=False)
    except OSError as exc:
        print(f"Command could not start: {exc}")
        return 127
    return completed.returncode


def run_gauntlet(run_command: Callable[[Command], int] = _run_command) -> int:
    for stage in GAUNTLET_STAGES:
        print(f"\n== {stage.name} ==")
        for command in stage.commands:
            exit_code = run_command(command)
            if exit_code != 0:
                print(f"{stage.name} failed with exit code {exit_code}.")
                return exit_code
        print(f"{stage.name} passed.")
    print("\nQA gauntlet passed.")
    return 0


def main() -> int:
    return run_gauntlet()


if __name__ == "__main__":
    raise SystemExit(main())
