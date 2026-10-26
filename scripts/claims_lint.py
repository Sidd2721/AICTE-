#!/usr/bin/env python3
"""Reject unsupported certainty claims in current project-facing documents."""

import argparse
import re
import sys
from pathlib import Path

BANNED: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("WCAG compliant", re.compile(r"\bWCAG\s+compliant\b", re.IGNORECASE)),
    ("production-ready", re.compile(r"\bproduction[- ]ready\b", re.IGNORECASE)),
    ("blockchain", re.compile(r"\bblockchain\b", re.IGNORECASE)),
    ("Merkle", re.compile(r"\bMerkle\b", re.IGNORECASE)),
    ("Pharmacy", re.compile(r"\bPharmacy\b", re.IGNORECASE)),
    ("100%", re.compile(r"\b100\s*%")),
    ("empirical speed claim", re.compile(r"\bempirical\b.*\b(speed|testing|baseline)\b", re.IGNORECASE)),
    ("x faster", re.compile(r"\b\d+\s*[x×]\s*faster\b", re.IGNORECASE)),
    ("superuser trigger claim", re.compile(r"even\s+from\s+superusers", re.IGNORECASE)),
    ("unbounded audit latency", re.compile(r"audit_verify\(\).*<\s*10\s*ms", re.IGNORECASE)),
)


def document_paths(inputs: list[str]) -> list[Path]:
    paths: list[Path] = []
    for value in inputs:
        path = Path(value)
        if path.is_dir():
            paths.extend(
                candidate
                for candidate in path.rglob("*.md")
                if candidate.name != "release-notes.md"
            )
        elif path.suffix.lower() in {".md", ".txt"}:
            paths.append(path)
    return sorted(set(paths))


def lint(paths: list[Path]) -> list[str]:
    findings: list[str] = []
    for path in paths:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for label, pattern in BANNED:
                if pattern.search(line):
                    findings.append(f"{path}:{number}: {label}: {line.strip()}")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "paths", nargs="*", default=["README.md", "DEMO.md", "INTEGRATION-GUIDE.md", "docs"]
    )
    args = parser.parse_args()
    findings = lint(document_paths(args.paths))
    if findings:
        print("Unsupported claims found:", file=sys.stderr)
        print("\n".join(findings), file=sys.stderr)
        return 1
    print("Claims lint passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
