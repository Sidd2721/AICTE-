import json
import subprocess
import sys
import uuid
from pathlib import Path
from app.domain.receipt import get_public_key_pem, sign_release_receipt

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def test_verify_receipt_cli_valid_and_tampered(tmp_path: Path):
    inst_id = str(uuid.uuid4())
    ref_no = "FDR-TEST-12345"
    path = "term_completion"
    token = sign_release_receipt(
        instrument_id=inst_id,
        instrument_ref_no=ref_no,
        path=path,
    )

    script = REPO_ROOT / "scripts" / "verify_receipt.py"
    key_file = tmp_path / "pub.pem"
    key_file.write_text(get_public_key_pem().decode("utf-8"), encoding="utf-8")

    # Test valid token
    res = subprocess.run(
        [sys.executable, str(script), token, "--key", str(key_file)],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"STDOUT: {res.stdout}\nSTDERR: {res.stderr}"
    assert "STATUS: VALID" in res.stdout
    data = json.loads(res.stdout.split("STATUS: VALID\n")[1])
    assert "receipt_id" in data
    assert "instrument_hash" in data
    assert data["path"] == path

    # Test tampered token
    parts = token.split(".")
    tampered_sig = parts[2][:10] + ("A" if parts[2][10] != "A" else "B") + parts[2][11:]
    tampered_token = f"{parts[0]}.{parts[1]}.{tampered_sig}"

    res_bad = subprocess.run(
        [sys.executable, str(script), tampered_token, "--key", str(key_file)],
        capture_output=True,
        text=True,
    )
    assert res_bad.returncode == 1
    assert "STATUS: INVALID" in res_bad.stderr
