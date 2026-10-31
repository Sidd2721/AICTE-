#!/usr/bin/env python3
"""Reject unsupported certainty claims and banned phrases in project-facing documents."""

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
    ("100%", re.compile(r"(?<![\[\-])\b100\s*%(?![\]\-])")),
    ("empirical speed claim", re.compile(r"\bempirical\b.*\b(speed|testing|baseline)\b", re.IGNORECASE)),
    ("x faster", re.compile(r"\b\d+\s*[x×]\s*faster\b", re.IGNORECASE)),
    ("superuser trigger claim", re.compile(r"even\s+from\s+superusers", re.IGNORECASE)),
    ("unbounded audit latency", re.compile(r"audit_verify\(\).*<\s*10\s*ms", re.IGNORECASE)),
    ("court-admissible", re.compile(r"\bcourt[- ]admissible\b", re.IGNORECASE)),
    ("eliminated", re.compile(r"\beliminated\b", re.IGNORECASE)),
    ("bulletproof", re.compile(r"\bbulletproof\b", re.IGNORECASE)),
    ("zero-trust", re.compile(r"\bzero[- ]trust\b", re.IGNORECASE)),
    ("statutory", re.compile(r"\bstatutory\b", re.IGNORECASE)),
    ("high-assurance", re.compile(r"\bhigh[- ]assurance\b", re.IGNORECASE)),
    ("zero risk", re.compile(r"\bzero\s+risk\b", re.IGNORECASE)),
    ("kernel-level", re.compile(r"\bkernel[- ]level\b", re.IGNORECASE)),
    ("zero downtime", re.compile(r"\bzero\s+downtime\b", re.IGNORECASE)),
    ("official emblem", re.compile(r"\bofficial\s+emblem\b", re.IGNORECASE)),
    ("for bank execution", re.compile(r"\bfor\s+bank\s+execution\b", re.IGNORECASE)),
    ("5,000+ Crores", re.compile(r"5,?000\+?\s*crores?", re.IGNORECASE)),
    ("10,000+ institutions", re.compile(r"10,?000\+?\s*institutions?", re.IGNORECASE)),
    ("8 to 10 years", re.compile(r"\b8\s*(?:to|-)\s*10\s*years\b", re.IGNORECASE)),
    ("Member Secretary joint lien", re.compile(r"Member\s+Secretary.*joint\s+lien", re.IGNORECASE)),
)


def document_paths(inputs: list[str]) -> list[Path]:
    paths: list[Path] = []
    for value in inputs:
        path = Path(value)
        if path.is_dir():
            paths.extend(
                candidate
                for candidate in path.rglob("*")
                if candidate.is_file()
                and candidate.suffix.lower() in {".md", ".txt", ".json", ".tsx", ".ts", ".py"}
                and candidate.name != "release-notes.md"
                and not any(part.startswith(".") or part in {"node_modules", ".venv", "dist", "build"} for part in candidate.parts)
            )
        elif path.is_file():
            paths.append(path)
    return sorted(set(paths))


def lint(paths: list[Path]) -> list[str]:
    findings: list[str] = []
    for path in paths:
        try:
            content = path.read_text(encoding="utf-8")
        except Exception:
            continue
        for number, line in enumerate(content.splitlines(), 1):
            for label, pattern in BANNED:
                if pattern.search(line):
                    findings.append(f"{path}:{number}: {label}: {line.strip()}")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "paths",
        nargs="*",
        default=[
            "README.md",
            "DEMO.md",
            "INTEGRATION-GUIDE.md",
            "docs",
            "frontend/src/lib",
            "frontend/src/routes",
            "backend/app/domain/reports_pdf.py",
        ],
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
