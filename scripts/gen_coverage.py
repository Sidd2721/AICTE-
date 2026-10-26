#!/usr/bin/env python3
"""Coverage generator: runs test IDs from docs/capability_map.json and writes docs/coverage.json.
Fails with non-zero exit if any test ID is missing or fails.
"""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAP_PATH = ROOT / "docs" / "capability_map.json"
OUT_PATH = ROOT / "docs" / "coverage.json"
BACKEND_DIR = ROOT / "backend"


def main() -> None:
    if not MAP_PATH.exists():
        print(f"Error: {MAP_PATH} not found", file=sys.stderr)
        sys.exit(1)

    with open(MAP_PATH, "r", encoding="utf-8") as f:
        cap_data = json.load(f)

    all_tests: list[str] = []
    for cap in cap_data.get("capabilities", []):
        all_tests.extend(cap.get("tests", []))

    unique_tests = list(dict.fromkeys(all_tests))
    print(f"Running {len(unique_tests)} capability-mapped tests via pytest...")

    cmd = ["uv", "run", "pytest", "-v", "--no-header", *unique_tests]
    proc = subprocess.run(cmd, cwd=str(BACKEND_DIR), capture_output=True, text=True)

    test_results: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        line = line.strip()
        for t in unique_tests:
            if t in line:
                if "PASSED" in line:
                    test_results[t] = "PASSED"
                elif "FAILED" in line:
                    test_results[t] = "FAILED"
                elif "ERROR" in line:
                    test_results[t] = "ERROR"
                elif "SKIPPED" in line:
                    test_results[t] = "SKIPPED"

    missing = [t for t in unique_tests if t not in test_results]
    failed = [t for t, res in test_results.items() if res != "PASSED"]

    capabilities_output = []
    for cap in cap_data.get("capabilities", []):
        tests_info = []
        cap_passed = True
        for t in cap.get("tests", []):
            st = test_results.get(t, "MISSING")
            if st != "PASSED":
                cap_passed = False
            tests_info.append({"test_id": t, "status": st})
        capabilities_output.append({
            "id": cap["id"],
            "name": cap["name"],
            "description": cap.get("description", ""),
            "status": "PASSED" if cap_passed else "FAILED",
            "tests": tests_info,
        })

    coverage_doc = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_capabilities": len(cap_data.get("capabilities", [])),
        "capabilities_passed": sum(1 for c in capabilities_output if c["status"] == "PASSED"),
        "total_tests": len(unique_tests),
        "tests_passed": sum(1 for res in test_results.values() if res == "PASSED"),
        "tests_failed": len(failed),
        "tests_missing": len(missing),
        "capabilities": capabilities_output,
    }

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(coverage_doc, f, indent=2)

    print(f"Coverage report written to {OUT_PATH}")
    print(f"Capabilities: {coverage_doc['capabilities_passed']}/{coverage_doc['total_capabilities']} passed")
    print(f"Tests: {coverage_doc['tests_passed']}/{coverage_doc['total_tests']} passed")

    if missing:
        print(f"ERROR: {len(missing)} mapped tests were missing or not executed: {missing}", file=sys.stderr)
        sys.exit(1)
    if failed:
        print(f"ERROR: {len(failed)} tests failed: {failed}", file=sys.stderr)
        sys.exit(1)
    if proc.returncode != 0:
        print(f"ERROR: pytest returned non-zero exit code {proc.returncode}", file=sys.stderr)
        sys.exit(proc.returncode)

    print("SUCCESS: All capability tests passed.")


if __name__ == "__main__":
    main()
