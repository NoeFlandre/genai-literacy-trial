from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_public_mkdocs_site_has_verified_navigation_and_ci_build() -> None:
    config = (REPO_ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    ci = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "site_name: GenAI Literacy Trial" in config
    for page in (
        "index.md",
        "reproducibility.md",
        "architecture.md",
        "data_flow.md",
        "diagrams.md",
        "cli.md",
        "configuration.md",
        "artifacts.md",
        "development.md",
        "privacy.md",
        "troubleshooting.md",
    ):
        assert page in config
    nav = config.split("\nnav:", maxsplit=1)[1]
    assert "agent_playbook.md" not in nav
    gauntlet = (REPO_ROOT / "scripts" / "qa_gauntlet.py").read_text(encoding="utf-8")
    assert '_uv_run("mkdocs", "build", "--strict"' in gauntlet
    assert "scripts/qa_gauntlet.py" in ci


def test_agent_playbook_documents_optional_manifest_hash_validation() -> None:
    playbook = (REPO_ROOT / "docs" / "agent_playbook.md").read_text(encoding="utf-8")

    assert "It does not compare content hashes." not in playbook
    assert "With `--manifest`, it also validates SHA-256 hashes" in playbook
