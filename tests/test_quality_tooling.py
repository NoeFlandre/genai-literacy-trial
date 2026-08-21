from __future__ import annotations

import json
import sys
import tomllib
from pathlib import Path

import mutmut.__main__ as mutmut_main
import pytest

from scripts.check_crap import _crap_failures, _function_coverage, _print_crap_failures, _radon_functions, calculate_crap
from scripts.check_crap import MAX_CRAP_SCORE, CrapResult, main as check_crap_main, parse_args
import scripts.run_mutation_gate as mutation_gate
from scripts.run_mutation_gate import MUTATION_PATTERNS, _metadata_failures, _report_mutation_gate, mutation_failures

def _repository_root() -> Path:
    for candidate in Path(__file__).resolve().parents:
        if (candidate / ".github" / "workflows" / "ci.yml").is_file():
            return candidate
    raise RuntimeError("repository root not found")


REPO_ROOT = _repository_root()


def test_quality_tooling_declares_ty_and_runs_it_in_ci() -> None:
    project = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dev_dependencies = project["dependency-groups"]["dev"]
    ci_text = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    gauntlet_text = (REPO_ROOT / "scripts" / "qa_gauntlet.py").read_text(encoding="utf-8")

    assert any(dependency == "ty" or dependency.startswith("ty ") or dependency.startswith("ty>") for dependency in dev_dependencies)
    assert '_uv_run("ty", "check", ".")' in gauntlet_text
    assert "scripts/qa_gauntlet.py" in ci_text
    assert '"coverage", "run", "--source=src,scripts"' in gauntlet_text
    assert '"radon", "cc", "src", "scripts", "-j"' in gauntlet_text


def test_crap_score_gate_is_strictly_below_six() -> None:
    assert MAX_CRAP_SCORE == 6.0
    assert CrapResult("module.py", "covered", 1, 5, 100.0).score < MAX_CRAP_SCORE
    assert CrapResult("module.py", "uncovered", 1, 5, 0.0).score >= MAX_CRAP_SCORE


def test_crap_failures_include_the_score_boundary() -> None:
    boundary = CrapResult("module.py", "boundary", 1, 2, 0.0)

    assert boundary.score == MAX_CRAP_SCORE
    assert _crap_failures([boundary]) == [boundary]


def test_crap_failures_are_printed_in_descending_score_order(capsys: pytest.CaptureFixture[str]) -> None:
    lower = CrapResult("module.py", "lower", 2, 2, 0.0)
    higher = CrapResult("module.py", "higher", 1, 5, 0.0)

    _print_crap_failures([lower, higher])

    assert capsys.readouterr().out == (
        "30.00  C=5  coverage=0.0%  module.py:1 higher\n"
        "6.00  C=2  coverage=0.0%  module.py:2 lower\n"
    )


def test_radon_functions_includes_top_level_functions_and_methods() -> None:
    payload = {
        "module.py": [
            {
                "type": "function",
                "name": "top_level",
                "methods": [{"name": "nested_method"}, "ignore this"],
            },
            {"type": "class", "methods": [{"name": "class_method"}]},
        ]
    }

    assert list(_radon_functions(payload)) == [
        ("module.py", payload["module.py"][0]),
        ("module.py", {"name": "nested_method"}),
        ("module.py", {"name": "class_method"}),
    ]


def test_function_coverage_returns_matching_summary_percent() -> None:
    coverage = {
        "files": {
            "module.py": {
                "functions": {
                    "target": {"start_line": 7, "summary": {"percent_covered": 87.5}},
                }
            }
        }
    }

    assert _function_coverage(coverage, "module.py", "target", 7) == 87.5


@pytest.mark.parametrize(
    "coverage",
    [
        {},
        {"files": []},
        {"files": {"module.py": []}},
        {"files": {"module.py": {"functions": []}}},
        {"files": {"module.py": {"functions": {"other": {"start_line": 7}}}}},
        {"files": {"module.py": {"functions": {"target": {"start_line": 7, "summary": []}}}}},
    ],
)
def test_function_coverage_defaults_to_zero_for_missing_or_malformed_data(coverage: dict[str, object]) -> None:
    assert _function_coverage(coverage, "module.py", "target", 7) == 0.0


def test_calculate_crap_combines_top_level_and_method_coverage() -> None:
    radon = {
        "module.py": [
            {
                "type": "function",
                "name": "top_level",
                "lineno": 3,
                "complexity": 5,
                "methods": [{"name": "class_method", "lineno": 12, "complexity": 2}],
            }
        ]
    }
    coverage = {
        "files": {
            "module.py": {
                "functions": {
                    "top_level": {"start_line": 3, "summary": {"percent_covered": 100.0}},
                    "class_method": {"start_line": 12, "summary": {"percent_covered": 50.0}},
                }
            }
        }
    }

    results = calculate_crap(coverage, radon)

    assert [(result.path, result.name, result.line, result.complexity, result.coverage_percent) for result in results] == [
        ("module.py", "top_level", 3, 5, 100.0),
        ("module.py", "class_method", 12, 2, 50.0),
    ]


@pytest.mark.parametrize("coverage_percent, expected_status", [(100.0, 0), (0.0, 1)])
def test_check_crap_main_reports_pass_or_failure(tmp_path: Path, capsys: pytest.CaptureFixture[str], coverage_percent: float, expected_status: int) -> None:
    coverage_path = tmp_path / "coverage.json"
    radon_path = tmp_path / "radon.json"
    coverage_path.write_text(
        json.dumps(
            {
                "files": {
                    "module.py": {
                        "functions": {
                            "target": {"start_line": 1, "summary": {"percent_covered": coverage_percent}}
                        }
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    radon_path.write_text(
        json.dumps({"module.py": [{"type": "function", "name": "target", "lineno": 1, "complexity": 5}]}),
        encoding="utf-8",
    )

    assert check_crap_main(["--coverage-json", str(coverage_path), "--radon-json", str(radon_path)]) == expected_status
    output = capsys.readouterr().out
    assert ("CRAP gate passed" in output) is (expected_status == 0)
    assert ("CRAP gate failed" in output) is (expected_status == 1)


def test_check_crap_main_reports_zero_functions_for_empty_payloads(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    coverage_path = tmp_path / "coverage.json"
    radon_path = tmp_path / "radon.json"
    coverage_path.write_text("{}", encoding="utf-8")
    radon_path.write_text("{}", encoding="utf-8")

    assert check_crap_main(["--coverage-json", str(coverage_path), "--radon-json", str(radon_path)]) == 0
    assert capsys.readouterr().out == "CRAP gate passed: 0 functions measured; maximum score 0.00 (< 6).\n"


def test_check_crap_cli_help_describes_both_json_inputs(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        parse_args(["--help"])

    assert exc_info.value.code == 0
    output = capsys.readouterr().out
    assert "\nFail when any source function has CRAP score at or above six.\n" in output
    assert "--coverage-json" in output
    assert "\n                        Coverage JSON produced by coverage json.\n" in output
    assert "--radon-json" in output
    assert "\n                        Radon JSON produced by radon cc -j.\n" in output


@pytest.mark.parametrize("provided", [["--radon-json", "radon.json"], ["--coverage-json", "coverage.json"]])
def test_check_crap_cli_requires_both_json_inputs(provided: list[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        parse_args(provided)

    assert exc_info.value.code == 2


def test_mutation_gate_reports_targeted_survivors_and_unchecked_mutants(tmp_path: Path) -> None:
    metadata_path = tmp_path / "src" / "module.py.meta"
    metadata_path.parent.mkdir()
    metadata_path.write_text(
        "{\"exit_code_by_key\": {"
        "\"genai_literacy_trial.quant_pipeline.x__read_input__mutmut_killed\": 1,"
        "\"genai_literacy_trial.quant_pipeline.x__read_input__mutmut_survived\": 0,"
        "\"genai_literacy_trial.quant_pipeline.x__read_input__mutmut_unchecked\": null,"
        "\"unrelated\": 0}}",
        encoding="utf-8",
    )

    assert mutation_failures(tmp_path) == [
        (
            "genai_literacy_trial.quant_pipeline.x__read_input__mutmut_survived",
            "survived",
        ),
        (
            "genai_literacy_trial.quant_pipeline.x__read_input__mutmut_unchecked",
            "not checked",
        ),
    ]


def test_mutation_gate_reports_missing_metadata(tmp_path: Path) -> None:
    assert mutation_failures(tmp_path) == [(str(tmp_path), "not checked")]


def test_mutation_gate_rejects_metadata_without_exit_codes(tmp_path: Path) -> None:
    metadata_path = tmp_path / "src" / "module.py.meta"
    metadata_path.parent.mkdir()
    metadata_path.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="no exit_code_by_key"):
        mutation_failures(tmp_path)


def test_mutation_gate_reports_metadata_path_for_non_string_mutant_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    metadata_path = tmp_path / "module.py.meta"
    monkeypatch.setattr(mutation_gate, "_metadata_exit_codes", lambda _: {None: 0})

    with pytest.raises(ValueError, match=str(metadata_path)):
        _metadata_failures(metadata_path)


def test_mutation_gate_reports_unknown_status_for_targeted_mutant(tmp_path: Path) -> None:
    metadata_path = tmp_path / "src" / "module.py.meta"
    metadata_path.parent.mkdir()
    metadata_path.write_text(
        json.dumps(
            {
                "exit_code_by_key": {
                    "genai_literacy_trial.quant_pipeline.x__read_input__mutmut_unknown": 999,
                }
            }
        ),
        encoding="utf-8",
    )

    assert mutation_failures(tmp_path) == [
        ("genai_literacy_trial.quant_pipeline.x__read_input__mutmut_unknown", "suspicious")
    ]


def test_mutation_gate_report_passes_when_no_failures(capsys: pytest.CaptureFixture[str]) -> None:
    _report_mutation_gate([])

    assert capsys.readouterr().out == "Mutation gate passed: all targeted mutants were killed.\n"


def test_mutation_gate_report_exits_and_lists_failures(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        _report_mutation_gate([("mutant", "survived"), ("other", "timeout")])

    assert exc_info.value.code == 1
    assert capsys.readouterr().out == (
        "Mutation gate failed: 2 targeted mutant(s) were not killed.\n"
        "  mutant: survived\n"
        "  other: timeout\n"
    )


def test_mutation_gate_main_preserves_explicit_cli_arguments(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[list[str], dict[str, object]]] = []

    monkeypatch.setattr(sys, "argv", ["run_mutation_gate.py", "results"])
    monkeypatch.setattr(mutmut_main, "cli", lambda **kwargs: calls.append((list(sys.argv), kwargs)))

    mutation_gate.main()

    assert calls == [(["run_mutation_gate.py", "results"], {"standalone_mode": False})]


def test_mutation_gate_main_builds_the_default_cli_invocation(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    calls: list[tuple[list[str], dict[str, object]]] = []

    monkeypatch.setattr(sys, "argv", ["run_mutation_gate.py"])
    monkeypatch.setattr(mutmut_main, "cli", lambda **kwargs: calls.append((list(sys.argv), kwargs)))
    monkeypatch.setattr(mutation_gate, "mutation_failures", lambda: [])

    mutation_gate.main()

    assert calls[0][0][:3] == ["run_mutation_gate.py", "run", "--max-children"]
    assert calls[0][0][3] == "8"
    assert calls[0][0][4:] == list(MUTATION_PATTERNS)
    assert calls[0][1] == {"standalone_mode": False}
    assert capsys.readouterr().out == "Mutation gate passed: all targeted mutants were killed.\n"


def test_mutation_gate_main_reports_default_run_failures(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "argv", ["run_mutation_gate.py"])
    monkeypatch.setattr(mutmut_main, "cli", lambda **kwargs: None)
    monkeypatch.setattr(mutation_gate, "mutation_failures", lambda: [("mutant", "survived")])

    with pytest.raises(SystemExit) as exc_info:
        mutation_gate.main()

    assert exc_info.value.code == 1
    assert capsys.readouterr().out == (
        "Mutation gate failed: 1 targeted mutant(s) were not killed.\n"
        "  mutant: survived\n"
    )


def test_mutation_gate_cleans_generated_artifacts_after_default_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mutants_dir = tmp_path / "mutants"
    mutants_dir.mkdir()
    (mutants_dir / "tests").mkdir()
    (mutants_dir / "tests" / "test_quant_stats.py").write_text("generated fixture\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["run_mutation_gate.py"])
    monkeypatch.setattr(mutmut_main, "cli", lambda **kwargs: None)
    monkeypatch.setattr(mutation_gate, "mutation_failures", lambda: [])

    mutation_gate.main()

    assert not mutants_dir.exists()


def test_mutation_gate_targets_the_exact_mutation_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "mutants").mkdir()
    removed: list[Path] = []

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(mutation_gate.shutil, "rmtree", lambda path: removed.append(path))

    mutation_gate._cleanup_mutation_artifacts()

    assert removed == [Path("mutants")]


def test_mutation_gate_selects_publication_regression_tests() -> None:
    project = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    selected_tests = project["tool"]["mutmut"]["pytest_add_cli_args_test_selection"]

    assert "tests/test_high_risk_contracts.py" in selected_tests
    assert any("publish_staged_public_outputs" in pattern for pattern in MUTATION_PATTERNS)
    assert MUTATION_PATTERNS[-2:] == ("scripts.check_crap.x_*", "scripts.run_mutation_gate.x_*")
