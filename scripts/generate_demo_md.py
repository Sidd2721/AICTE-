#!/usr/bin/env python3
"""Generate DEMO.md strictly from docs/guide.json (CHARTER G1).

Guarantees zero documentation drift. Titles match scripts/demo_steps.py exactly.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GUIDE_JSON = ROOT / "docs" / "guide.json"
DEMO_MD = ROOT / "DEMO.md"


def generate_demo_md() -> None:
    data = json.loads(GUIDE_JSON.read_text(encoding="utf-8"))

    lines = [
        "# AICTE Security Deposit / FDR Portal — Live Demo Script",
        "",
        "**AICTE PS 26265** | Branch: `sprint/present-anywhere` | Tag: `sprint2-start`",
        "",
        "> **IMPORTANT**: All bank and email interactions are **SIMULATED** (transparently labelled).",
        "> All institutions, deposit amounts, and reference numbers are **synthetic**.",
        "> DSC receipts prove document signer, **not bank confirmations**.",
        "> Rule values are marked **DEMO**, pending official handbook confirmation.",
        "",
        "---",
        "",
        "## Prerequisites",
        "",
        "```powershell",
        "# 1. Preflight system health check",
        "uv run python scripts/doctor.py",
        "",
        "# 2. Re-seed DB and run all 7 problem statement demo steps:",
        "powershell -ExecutionPolicy Bypass -File scripts/run-demo.ps1 -Reset",
        "```",
        "",
        "The demo server runs at **http://localhost:8000**.",
        "",
        "---",
        "",
    ]

    for s in data["steps"]:
        num = s["step_number"]
        title = s["title"]
        persona = s["persona"]
        email = s["email"]
        route = s["route"]
        goal = s["goal"]
        why = s["why"]
        expect = s["expect"]
        do_items = s["do"]

        lines.extend([
            f"## STEP {num}: {title}",
            "",
            f"**Actor:** {persona} (`{email}`)  ",
            f"**Route:** `{route}`  ",
            f"**Goal:** {goal}",
            "",
            "### Actions to Perform:",
        ])
        for idx, item in enumerate(do_items, 1):
            lines.append(f"{idx}. {item}")

        lines.extend([
            "",
            f"**Expected Outcome:** {expect}",
            "",
            f"**Why this matters:** {why}",
            "",
            "---",
            "",
        ])

    lines.extend([
        "## Demo Credentials Matrix",
        "",
        "| Persona Role | Email | Region | Permission Scope | Password |",
        "| :--- | :--- | :--- | :--- | :--- |",
        "| **Institution** | `inst.north1@example.com` | NR | Submits FDR, requests release | `AdminSecure2026!` |",
        "| **Regional Officer** | `officer.north@example.com` | NR | Requests bank confirmation, verifies release | `AdminSecure2026!` |",
        "| **Regional Checker** | `checker.north@example.com` | NR | Regional inspection & notes | `AdminSecure2026!` |",
        "| **Bureau Head** | `bureau@example.com` | ALL | Approves release (checker), all reports | `AdminSecure2026!` |",
        "| **Auditor** | `auditor@example.com` | ALL | Read-only audit log & instruments | `AdminSecure2026!` |",
        "",
        "*(All demo personas are accessible via 1-click login buttons on `/login` and `/guide`)*",
        "",
    ])

    DEMO_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] Generated {DEMO_MD} successfully from {GUIDE_JSON}")


if __name__ == "__main__":
    generate_demo_md()
