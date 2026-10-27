#!/usr/bin/env python3
"""Verification test suite for demo_data.py CSV import validation cases (Requirement 2.4).

Verifies:
1. Happy path CSV import
2. Bad IFSC rejection
3. Duplicate ref_no across different institutions (flagged without leaking other institution)
4. Negative amount rejection
"""

import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def run_import(data_dir: Path, partial: bool = False) -> subprocess.CompletedProcess[str]:
    cmd = ["uv", "run", "python", str(ROOT / "scripts" / "demo_data.py"), "import", "--dir", str(data_dir)]
    if partial:
        cmd.append("--partial")
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)


def test_csv_import_cases() -> None:
    print("[TEST] Running CSV Import validation suite...")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # 1. Base valid institutions
        inst_csv = tmp_path / "institutions.csv"
        with open(inst_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["permanent_id", "name", "region", "is_government", "leased_private", "programmes", "contact_email"])
            writer.writerow(["P-TEST-INST-01", "Test Institute Alpha", "NR", False, False, '[{"category":"Engineering and Technology","level":"UG"}]', "alpha@example.com"])
            writer.writerow(["P-TEST-INST-02", "Test Institute Beta", "WR", False, False, '[{"category":"Engineering and Technology","level":"UG"}]', "beta@example.com"])

        # ---------------------------------------------------------
        # Case 1: Happy Path
        # ---------------------------------------------------------
        instr_csv = tmp_path / "instruments.csv"
        with open(instr_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["institution_permanent_id", "ref_no", "bank_code", "ifsc", "amount_paise", "issue_date", "maturity_date", "kind", "lifecycle", "lien_marked"])
            writer.writerow(["P-TEST-INST-01", "FDR-HAPPY-001", "SBIN", "SBIN0001234", 350000000, "2024-01-01", "2034-01-01", "FDR", "active", True])

        res_happy = run_import(tmp_path)
        assert res_happy.returncode == 0, f"Happy path import failed: {res_happy.stderr}\n{res_happy.stdout}"
        assert "[OK] CSV Import successful" in res_happy.stderr or "[OK] CSV Import successful" in res_happy.stdout
        print("  -> Case 1 (Happy path): PASSED")

        # ---------------------------------------------------------
        # Case 2: Bad IFSC
        # ---------------------------------------------------------
        with open(instr_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["institution_permanent_id", "ref_no", "bank_code", "ifsc", "amount_paise", "issue_date", "maturity_date", "kind", "lifecycle", "lien_marked"])
            writer.writerow(["P-TEST-INST-01", "FDR-BAD-IFSC", "SBIN", "INVALID_IFSC_99", 350000000, "2024-01-01", "2034-01-01", "FDR", "pending", False])

        res_bad_ifsc = run_import(tmp_path)
        assert res_bad_ifsc.returncode != 0, "Bad IFSC should have failed validation"
        assert "Invalid IFSC format" in res_bad_ifsc.stdout or "Invalid IFSC format" in res_bad_ifsc.stderr
        print("  -> Case 2 (Bad IFSC rejected): PASSED")

        # ---------------------------------------------------------
        # Case 3: Duplicate ref across institutions (No leak of other institution)
        # ---------------------------------------------------------
        # FDR-HAPPY-001 belongs to P-TEST-INST-01. Now P-TEST-INST-02 attempts to use FDR-HAPPY-001!
        with open(instr_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["institution_permanent_id", "ref_no", "bank_code", "ifsc", "amount_paise", "issue_date", "maturity_date", "kind", "lifecycle", "lien_marked"])
            writer.writerow(["P-TEST-INST-02", "FDR-HAPPY-001", "SBIN", "SBIN0001234", 350000000, "2024-01-01", "2034-01-01", "FDR", "pending", False])

        res_dup_ref = run_import(tmp_path)
        assert res_dup_ref.returncode != 0, "Duplicate cross-institution ref should have failed"
        output_text = res_dup_ref.stdout + res_dup_ref.stderr
        assert "Duplicate reference number across institutions" in output_text
        # Security invariant: does NOT leak the name of the other institution!
        assert "Test Institute Alpha" not in output_text, "Leaked other institution name!"
        assert "P-TEST-INST-01" not in output_text, "Leaked other institution permanent_id!"
        print("  -> Case 3 (Duplicate cross-institution ref flagged without leak): PASSED")

        # ---------------------------------------------------------
        # Case 4: Negative amount
        # ---------------------------------------------------------
        with open(instr_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["institution_permanent_id", "ref_no", "bank_code", "ifsc", "amount_paise", "issue_date", "maturity_date", "kind", "lifecycle", "lien_marked"])
            writer.writerow(["P-TEST-INST-01", "FDR-NEG-001", "SBIN", "SBIN0001234", -50000000, "2024-01-01", "2034-01-01", "FDR", "pending", False])

        res_neg = run_import(tmp_path)
        assert res_neg.returncode != 0, "Negative amount should have failed validation"
        output_neg = res_neg.stdout + res_neg.stderr
        assert "amount_paise" in output_neg and ("greater than 0" in output_neg or "strictly positive" in output_neg)
        print("  -> Case 4 (Negative amount rejected): PASSED")

    print("\n[OK] All 4 CSV import validation cases passed!")

if __name__ == "__main__":
    test_csv_import_cases()
