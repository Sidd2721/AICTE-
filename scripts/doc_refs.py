#!/usr/bin/env python3
"""Check that scripts named by project documents exist at the named path."""

import argparse
import re
import sys
from pathlib import Path

SCRIPT_REFERENCE = re.compile(r"(?<![\w-])((?:backend/)?scripts/[\w.-]+\.py)")


def document_paths(inputs: list[str]) -> list[Path]:
    paths: list[Path] = []
    for value in inputs:
        path = Path(value)
        if path.is_dir():
            paths.extend(path.rglob("*.md"))
        elif path.suffix.lower() in {".md", ".txt"}:
            paths.append(path)
    return sorted(set(paths))


def check(root: Path, paths: list[Path]) -> list[str]:
    findings: list[str] = []
    for document in paths:
        text = document.read_text(encoding="utf-8")
        for number, line in enumerate(text.splitlines(), 1):
            for reference in SCRIPT_REFERENCE.findall(line):
                if not (root / reference).is_file():
                    findings.append(f"{document}:{number}: missing script: {reference}")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "paths", nargs="*", default=["README.md", "DEMO.md", "INTEGRATION-GUIDE.md", "docs"]
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    findings = check(root, document_paths(args.paths))
    if findings:
        print("Missing document references:", file=sys.stderr)
        print("\n".join(findings), file=sys.stderr)
        return 1
    print("Document reference check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
