from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

LOCAL_PATTERN_FILENAME = "privacy_patterns.local.yml"
RULE_LOCAL_PATTERN = "local_pattern"
RULE_DENIED_SUFFIX = "denied_suffix"

DEFAULT_DENIED_SUFFIXES = {
    ".docx",
    ".htm",
    ".html",
    ".ipynb",
    ".mhtml",
    ".pptx",
    ".xlsx",
}

SKIPPED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "archive",
    "clean_private_data",
    "private",
    "private_outputs",
}

TEXT_SUFFIXES = {
    ".cff",
    ".csv",
    ".dockerignore",
    ".gitignore",
    ".md",
    ".py",
    ".toml",
    ".txt",
    ".yml",
    ".yaml",
}

EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
ACADEMIC_DOMAIN_RE = re.compile(r"\b[A-Z0-9.-]+\.edu\b", re.IGNORECASE)
BANNER_RE = re.compile(r"\b(?:banner\s*id|student\s*id)\b|\b\d{8,9}\b", re.IGNORECASE)
TRANSCRIPT_RE = re.compile(r"\b(?:User|GPT)\d+\b")
COURSE_EXPORT_RE = re.compile(
    r"\b(?:" + "CSE" + r"\s*374|" + "CSE" + r"374|section\s+[ABC]|Group\s+[ABC]\s+Roster)\b",
    re.IGNORECASE,
)
PRIVACY_TEXT_RULES = (
    ("email", EMAIL_RE),
    ("academic_domain", ACADEMIC_DOMAIN_RE),
    ("banner_or_student_id", BANNER_RE),
    ("raw_transcript_column", TRANSCRIPT_RE),
    ("course_export_identifier", COURSE_EXPORT_RE),
)


@dataclass(frozen=True)
class PrivacyFinding:
    path: Path
    rule: str
    evidence: str


def _is_public_file(path: Path, root: Path) -> bool:
    if not path.is_file():
        return False
    relative_parts = path.relative_to(root).parts
    if any(part in SKIPPED_DIRS for part in relative_parts):
        return False
    return path.name != LOCAL_PATTERN_FILENAME


def iter_public_files(root: Path) -> list[Path]:
    return [path for path in sorted(root.rglob("*")) if _is_public_file(path, root)]


def load_local_patterns(path: Path) -> list[str]:
    if not path.exists():
        return []
    patterns: list[str] = []
    in_patterns = False
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        in_patterns, pattern = _parse_local_pattern_line(raw_line, in_patterns)
        if pattern is not None:
            patterns.append(pattern)
    return patterns


def _parse_local_pattern_line(raw_line: str, in_patterns: bool) -> tuple[bool, str | None]:
    line = raw_line.strip()
    if not line or line.startswith("#"):
        return in_patterns, None
    return _parse_nonempty_pattern_line(line, in_patterns)


def _parse_nonempty_pattern_line(line: str, in_patterns: bool) -> tuple[bool, str | None]:
    if line == "patterns:":
        return True, None
    if not in_patterns or not line.startswith("- "):
        return in_patterns, None
    pattern = line[2:].strip().strip("'\"")
    return in_patterns, pattern or None


def _read_text_if_supported(path: Path) -> str:
    if path.suffix and path.suffix not in TEXT_SUFFIXES:
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ""


def _normalise_local_pattern_text(value: str) -> str:
    normalized = re.sub(r"[\\/_-]", " ", value)
    return re.sub(r"\s+", " ", normalized).strip().lower()


def _path_pattern_findings(path: Path, relative: Path, local_patterns: list[str]) -> list[PrivacyFinding]:
    findings: list[PrivacyFinding] = []
    relative_path = _normalise_local_pattern_text(relative.as_posix())
    for pattern in local_patterns:
        if _normalise_local_pattern_text(pattern) in relative_path:
            findings.append(PrivacyFinding(path=relative, rule=RULE_LOCAL_PATTERN, evidence=pattern[:80]))
            break
    return findings


def _text_rule_findings(relative: Path, text: str) -> list[PrivacyFinding]:
    findings: list[PrivacyFinding] = []
    for rule, regex in PRIVACY_TEXT_RULES:
        match = regex.search(text)
        if match:
            findings.append(PrivacyFinding(path=relative, rule=rule, evidence=match.group(0)[:80]))
    return findings


def _local_text_findings(relative: Path, text: str, local_patterns: list[str]) -> list[PrivacyFinding]:
    lower_text = text.lower()
    for pattern in local_patterns:
        if pattern.lower() in lower_text:
            return [PrivacyFinding(path=relative, rule=RULE_LOCAL_PATTERN, evidence=pattern[:80])]
    return []


def scan_file(path: Path, *, root: Path, local_patterns: list[str]) -> list[PrivacyFinding]:
    relative = path.relative_to(root)
    findings = _path_pattern_findings(path, relative, local_patterns) if local_patterns else []

    if path.suffix.lower() in DEFAULT_DENIED_SUFFIXES:
        findings.append(PrivacyFinding(path=relative, rule=RULE_DENIED_SUFFIX, evidence=path.suffix.lower()))
        return findings

    text = _read_text_if_supported(path)
    if not text:
        return findings

    findings.extend(_text_rule_findings(relative, text))
    findings.extend(_local_text_findings(relative, text, local_patterns))
    return findings


def scan_public_tree(root: Path, *, local_pattern_file: Path | None = None) -> list[PrivacyFinding]:
    pattern_file = local_pattern_file or root / LOCAL_PATTERN_FILENAME
    local_patterns = load_local_patterns(pattern_file)
    findings: list[PrivacyFinding] = []
    for path in iter_public_files(root):
        findings.extend(scan_file(path, root=root, local_patterns=local_patterns))
    return findings
