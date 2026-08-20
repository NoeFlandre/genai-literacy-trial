#!/usr/bin/env python
from __future__ import annotations

import argparse
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
import json
from pathlib import Path
from typing import cast


MAX_CRAP_SCORE = 6.0


@dataclass(frozen=True)
class CrapResult:
    path: str
    name: str
    line: int
    complexity: int
    coverage_percent: float

    @property
    def score(self) -> float:
        uncovered = 1 - self.coverage_percent / 100
        return self.complexity**2 * uncovered**3 + self.complexity


def _radon_functions(payload: Mapping[str, Sequence[Mapping[str, object]]]) -> Iterator[tuple[str, dict[str, object]]]:
    for path, entries in payload.items():
        for entry in entries:
            for function in _radon_entry_functions(entry):
                yield path, function


def _radon_entry_functions(entry: Mapping[str, object]) -> Iterator[dict[str, object]]:
    if entry.get("type") == "function":
        yield cast(dict[str, object], entry)
    methods = entry.get("methods", [])
    if not isinstance(methods, list):
        return
    for method in methods:
        if isinstance(method, dict):
            yield cast(dict[str, object], method)


def _as_mapping(value: object) -> Mapping[str, object]:
    if isinstance(value, dict):
        return cast(Mapping[str, object], value)
    return {}


def _matching_function(functions: Mapping[str, object], name: str, line: int) -> dict[str, object] | None:
    for candidate_name, candidate in functions.items():
        if candidate_name != name:
            continue
        if not isinstance(candidate, dict):
            continue
        if candidate.get("start_line") == line:
            return cast(dict[str, object], candidate)
    return None


def _function_coverage(coverage_file: Mapping[str, object], path: str, name: str, line: int) -> float:
    files = _as_mapping(coverage_file.get("files", {}))
    file_data = _as_mapping(files.get(path, {}))
    functions = _as_mapping(file_data.get("functions", {}))
    candidate = _matching_function(functions, name, line)
    if candidate is None:
        return 0.0
    summary = _as_mapping(candidate.get("summary", {}))
    return float(cast(float, summary.get("percent_covered", 0.0)))


def calculate_crap(coverage_payload: Mapping[str, object], radon_payload: Mapping[str, Sequence[Mapping[str, object]]]) -> list[CrapResult]:
    results: list[CrapResult] = []
    for path, function in _radon_functions(radon_payload):
        name = str(function["name"])
        line = cast(int, function["lineno"])
        results.append(
            CrapResult(
                path=path,
                name=name,
                line=line,
                complexity=cast(int, function["complexity"]),
                coverage_percent=_function_coverage(coverage_payload, path, name, line),
            )
        )
    return results


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fail when any source function has CRAP score at or above six.")
    parser.add_argument("--coverage-json", type=Path, required=True, help="Coverage JSON produced by coverage json.")
    parser.add_argument("--radon-json", type=Path, required=True, help="Radon JSON produced by radon cc -j.")
    return parser.parse_args(argv)


def _crap_failures(results: list[CrapResult]) -> list[CrapResult]:
    return [result for result in results if result.score >= MAX_CRAP_SCORE]


def _print_crap_failures(failures: list[CrapResult]) -> None:
    for result in sorted(failures, key=lambda item: item.score, reverse=True):
        print(f"{result.score:.2f}  C={result.complexity}  coverage={result.coverage_percent:.1f}%  {result.path}:{result.line} {result.name}")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    coverage_payload = json.loads(args.coverage_json.read_text(encoding="utf-8"))
    radon_payload = json.loads(args.radon_json.read_text(encoding="utf-8"))
    results = calculate_crap(coverage_payload, radon_payload)
    failures = _crap_failures(results)
    if failures:
        print(f"CRAP gate failed: {len(failures)} function(s) scored >= {MAX_CRAP_SCORE:g}.")
        _print_crap_failures(failures)
        return 1
    maximum = max((result.score for result in results), default=0.0)
    print(f"CRAP gate passed: {len(results)} functions measured; maximum score {maximum:.2f} (< {MAX_CRAP_SCORE:g}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
