"""Tests for scripts/doc_refs.py verifying documentation reference and hygiene scanning."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

# Import check, document_paths, main directly
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.doc_refs import check, document_paths, main


def test_doc_refs_repo_documentation_is_clean() -> None:
    """The repository documentation contains no broken script references or forbidden absolute URLs."""
    targets = [str(ROOT / p) for p in ["README.md", "DEMO.md", "INTEGRATION-GUIDE.md", "docs"]]
    docs = document_paths(targets)
    findings = check(ROOT, docs)
    assert findings == [], f"Unexpected doc_refs findings in repository: {findings}"


def test_doc_refs_negative_control_planted_absolute_file_url(tmp_path: Path) -> None:
    """Negative control: a planted file-scheme absolute URL in a document must fail the scan."""
    bad_doc = tmp_path / "planted_bad_doc.md"
    planted_url = "file:" + "///etc/passwd/test_leak.txt"
    bad_doc.write_text(
        f"# Test Title\nSee documentation at {planted_url}\n",
        encoding="utf-8",
    )

    findings = check(ROOT, [bad_doc])
    assert len(findings) == 1
    assert "absolute file URL rejected" in findings[0]
    assert planted_url in findings[0]


def test_doc_refs_negative_control_planted_missing_script(tmp_path: Path) -> None:
    """Negative control: a reference to a nonexistent script in a document must fail the scan."""
    bad_doc = tmp_path / "planted_missing_script.md"
    bad_doc.write_text(
        "# Heading\nRun backend/scripts/planted_nonexistent_tool_12345.py to proceed.\n",
        encoding="utf-8",
    )

    findings = check(ROOT, [bad_doc])
    assert len(findings) == 1
    assert "missing script: backend/scripts/planted_nonexistent_tool_12345.py" in findings[0]


def test_doc_refs_negative_control_cli_exit_code(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """Negative control: running doc_refs.py CLI against a planted invalid doc exits with code 1."""
    bad_doc = tmp_path / "cli_planted_bad.md"
    planted_url = "file:" + "///c:/local/planted_violation.md"
    bad_doc.write_text(f"Invalid reference: {planted_url}\n", encoding="utf-8")

    monkeypatch.setattr(sys, "argv", ["doc_refs.py", str(bad_doc)])
    exit_code = main()
    assert exit_code == 1
    captured = capsys.readouterr()
    assert "Document reference & hygiene check failed" in captured.err
    assert "absolute file URL rejected" in captured.err
