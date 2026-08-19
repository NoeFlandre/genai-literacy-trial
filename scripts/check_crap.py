#!/usr/bin/env python
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Iterator, cast


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


def _radon_functions(payload: dict[str, list[dict[str, object]]]) -> Iterator[tuple[str, dict[str, object]]]:
    for path, entries in payload.items():
        for entry in entries:
            if entry.get("type") == "function":
                yield path, entry
            methods = cast(list[object], entry.get("methods", []))
            for method in methods:
                if isinstance(method, dict):
                    yield path, method


def _function_coverage(coverage_file: dict[str, object], path: str, name: str, line: int) -> float:
    files = coverage_file.get("files", {})
    if not isinstance(files, dict):
        return 0.0
    file_data = files.get(path, {})
    if not isinstance(file_data, dict):
        return 0.0
    functions = file_data.get("functions", {})
    if not isinstance(functions, dict):
        return 0.0
    for candidate_name, candidate in functions.items():
        if candidate_name == name and isinstance(candidate, dict) and candidate.get("start_line") == line:
            summary = candidate.get("summary", {})
            if isinstance(summary, dict):
                return float(summary.get("percent_covered", 0.0))
    return 0.0


def calculate_crap(coverage_payload: dict[str, object], radon_payload: dict[str, list[dict[str, object]]]) -> list[CrapResult]:
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


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    coverage_payload = json.loads(args.coverage_json.read_text(encoding="utf-8"))
    radon_payload = json.loads(args.radon_json.read_text(encoding="utf-8"))
    results = calculate_crap(coverage_payload, radon_payload)
    failures = [result for result in results if result.score >= MAX_CRAP_SCORE]
    if failures:
        print(f"CRAP gate failed: {len(failures)} function(s) scored >= {MAX_CRAP_SCORE:g}.")
        for result in sorted(failures, key=lambda item: item.score, reverse=True):
            print(f"{result.score:.2f}  C={result.complexity}  coverage={result.coverage_percent:.1f}%  {result.path}:{result.line} {result.name}")
        return 1
    maximum = max((result.score for result in results), default=0.0)
    print(f"CRAP gate passed: {len(results)} functions measured; maximum score {maximum:.2f} (< {MAX_CRAP_SCORE:g}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
