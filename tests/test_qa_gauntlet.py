from __future__ import annotations

from pathlib import Path
import sys

import pytest

from scripts.qa_gauntlet import Command, GAUNTLET_STAGES, _run_command, run_gauntlet


def test_gauntlet_has_the_required_deterministic_stage_order() -> None:
    assert tuple(stage.name for stage in GAUNTLET_STAGES) == (
        "baseline",
        "ruff",
        "ty",
        "tests",
        "acceptance tests",
        "architecture checks",
        "CRAP",
        "mutation tests",
        "smoke test",
        "diff review",
    )


def test_gauntlet_contains_the_repository_commands_for_each_risk_area() -> None:
    commands = [" ".join(command.argv) for stage in GAUNTLET_STAGES for command in stage.commands]
    command_text = "\n".join(commands)

    assert "uv lock --check" in command_text
    assert "ruff check ." in command_text
    assert "ty check ." in command_text
    assert "coverage run --source=src,scripts -m pytest" in command_text
    assert "tests/test_high_risk_contracts.py" in command_text
    assert "tests/test_architecture.py" in command_text
    assert "radon cc src scripts -j" in command_text
    assert "scripts/run_mutation_gate.py" in command_text
    assert "scripts/reproduce_small.py" in command_text
    assert "git diff --check HEAD" in command_text


def test_gauntlet_stops_at_the_first_failed_command(capsys: pytest.CaptureFixture[str]) -> None:
    calls: list[tuple[str, ...]] = []
    first_command = GAUNTLET_STAGES[0].commands[0].argv

    def fail_first(command: Command) -> int:
        calls.append(command.argv)
        return 7 if len(calls) == 1 else 0

    assert run_gauntlet(fail_first) == 7
    assert calls == [first_command]
    assert "baseline failed with exit code 7" in capsys.readouterr().out


def test_run_command_handles_terminal_file_and_startup_failures(tmp_path: Path) -> None:
    output_path = tmp_path / "radon.json"

    assert _run_command(Command((sys.executable, "-c", "print('terminal')"))) == 0
    assert _run_command(Command((sys.executable, "-c", "print('file')"), stdout_path=output_path)) == 0
    assert output_path.read_text(encoding="utf-8") == "file\n"
    assert _run_command(Command((str(tmp_path / "missing-command"),))) == 127
