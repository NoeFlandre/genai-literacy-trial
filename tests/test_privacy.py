from __future__ import annotations

from pathlib import Path

from genai_literacy_trial.privacy import (
    DEFAULT_DENIED_SUFFIXES,
    PrivacyFinding,
    iter_public_files,
    load_local_patterns,
    scan_file,
    scan_public_tree,
)


def test_iter_public_files_skips_archive_and_git(tmp_path: Path) -> None:
    (tmp_path / "archive").mkdir()
    (tmp_path / "archive" / "raw.xlsx").write_text("private")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("private")
    (tmp_path / "README.md").write_text("public")

    files = list(iter_public_files(tmp_path))

    assert files == [tmp_path / "README.md"]


def test_scan_file_detects_email_ids_names_transcripts_and_denied_suffixes(tmp_path: Path) -> None:
    local_name = "Jane" + " " + "Student"
    local_patterns = [local_name]
    unsafe = tmp_path / "unsafe.md"
    unsafe_address = "jane.student" + "@" + "academic-domain" + "." + "edu"
    banner_label = "Banner" + " " + "ID"
    transcript_user = "User" + "1"
    transcript_gpt = "GPT" + "1"
    unsafe.write_text(
        f"Contact {unsafe_address} for {banner_label} {'0123' + '45678'}. "
        f"{local_name} appears in content. {transcript_user} and {transcript_gpt} are raw transcript columns.",
        encoding="utf-8",
    )

    findings = scan_file(unsafe, root=tmp_path, local_patterns=local_patterns)
    rules = {finding.rule for finding in findings}

    assert {"email", "academic_domain", "banner_or_student_id", "local_pattern", "raw_transcript_column"} <= rules

    denied = scan_file(tmp_path / "raw.xlsx", root=tmp_path, local_patterns=[])
    assert denied == [
        PrivacyFinding(
            path=Path("raw.xlsx"),
            rule="denied_suffix",
            evidence=".xlsx",
        )
    ]
    assert ".xlsx" in DEFAULT_DENIED_SUFFIXES


def test_scan_file_detects_local_pattern_in_file_path(tmp_path: Path) -> None:
    local_pattern = "Jane" + " " + "Student"
    public_file = tmp_path / ("Jane" + "_" + "Student" + "_summary.csv")
    public_file.write_text("aggregate students\nall cohorts retained\n", encoding="utf-8")

    findings = scan_file(public_file, root=tmp_path, local_patterns=[local_pattern])

    assert findings == [
        PrivacyFinding(
            path=Path("Jane_Student_summary.csv"),
            rule="local_pattern",
            evidence=local_pattern,
        )
    ]


def test_load_local_patterns_reads_ignored_yaml_shape(tmp_path: Path) -> None:
    config = tmp_path / "privacy_patterns.local.yml"
    first_pattern = "Jane" + " " + "Student"
    second_pattern = "private-course-export"
    config.write_text(
        f"""
patterns:
  - {first_pattern}
  - {second_pattern}
""".strip(),
        encoding="utf-8",
    )

    assert load_local_patterns(config) == [first_pattern, second_pattern]


def test_scan_public_tree_returns_no_findings_for_safe_repo(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "module.py").write_text("VALUE = 'aggregate only'\\n", encoding="utf-8")
    (tmp_path / "paper_outputs").mkdir()
    (tmp_path / "paper_outputs" / "summary.csv").write_text("metric,value\\nretained_students,45\\n", encoding="utf-8")

    assert scan_public_tree(tmp_path) == []


def test_scan_public_tree_detects_local_pattern_in_path_from_config(tmp_path: Path) -> None:
    public_file = tmp_path / ("Jane" + "_" + "Student" + "_summary.csv")
    public_file.write_text("final cohort totals\n", encoding="utf-8")

    pattern_file = tmp_path / "privacy_patterns.local.yml"
    local_pattern = "Jane" + " " + "Student"
    pattern_file.write_text(
        f"""
patterns:
  - {local_pattern}
""".strip(),
        encoding="utf-8",
    )

    assert scan_public_tree(tmp_path, local_pattern_file=pattern_file) == [
        PrivacyFinding(
            path=Path("Jane_Student_summary.csv"),
            rule="local_pattern",
            evidence=local_pattern,
        )
    ]
