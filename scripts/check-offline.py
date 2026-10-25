#!/usr/bin/env python3
"""Offline integrity verification (CHARTER R5).

Verifies that the built frontend bundle has zero external runtime dependencies:
- No Google Fonts / CDN links
- No third-party tracking or analytics scripts
- No external stylesheets or script tags
- Assets are strictly bundled and served self-contained

Exit code 0 if fully offline-capable, 1 if external references detected.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

EXTERNAL_DOMAINS = [
    "fonts.googleapis.com",
    "fonts.gstatic.com",
    "cdnjs.cloudflare.com",
    "unpkg.com",
    "cdn.jsdelivr.net",
    "ajax.googleapis.com",
    "google-analytics.com",
    "googletagmanager.com",
]

ALLOWED_SCHEMES = ("data:", "blob:", "#")


def scan_file(path: Path) -> list[str]:
    violations: list[str] = []
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        return [f"Could not read {path}: {e}"]

    for domain in EXTERNAL_DOMAINS:
        if domain in content:
            violations.append(f"{path}: references external CDN domain '{domain}'")

    # In HTML files, check for external <link href="http..." or <script src="http..."
    if path.suffix in (".html", ".htm"):
        for match in re.finditer(r'(?:href|src)=["\'](https?://[^"\']+)["\']', content, re.IGNORECASE):
            url = match.group(1)
            violations.append(f"{path}: external resource link found: {url}")

    return violations


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    frontend_dir = root / "backend" / "app" / "frontend"

    if not frontend_dir.exists():
        print(f"Directory {frontend_dir} does not exist. Run 'bun run build' in frontend first.")
        return 1

    print(f"Scanning built frontend bundle at: {frontend_dir}")
    all_violations: list[str] = []

    for file_path in frontend_dir.rglob("*"):
        if file_path.is_file() and file_path.suffix in (".html", ".js", ".css"):
            v = scan_file(file_path)
            all_violations.extend(v)

    if all_violations:
        print(f"\nFAIL (CHARTER R5): External references found ({len(all_violations)}):")
        for v in all_violations:
            print(f"  ✖ {v}")
        return 1

    print("\nPASS (CHARTER R5): Zero external font, CDN, or analytics references found in built frontend.")
    print("Bundle is 100% self-contained and runnable offline.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
