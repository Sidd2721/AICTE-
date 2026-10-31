#!/usr/bin/env python3
"""Pre-show Health Check for AICTE FDR Portal Demo.

Usage:
    python scripts/preshow_check.py [TARGET_URL]

Runs fast, read-only live verification checks to ensure the deployment is healthy,
responsive, and ready for judge presentation. Exits 0 on all-pass, 1 on failure.
"""

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Tuple

DEFAULT_TARGET = "https://aicte-1-59pn.onrender.com"


def http_request(
    url: str,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    data: bytes | None = None,
    timeout: float = 12.0,
) -> Tuple[int, dict[str, str], bytes]:
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("User-Agent", "AICTE-Preshow-Check/1.0")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp_headers = {k.lower(): v for k, v in resp.headers.items()}
            return resp.status, resp_headers, resp.read()
    except urllib.error.HTTPError as e:
        resp_headers = {k.lower(): v for k, v in e.headers.items()}
        return e.code, resp_headers, e.read()
    except Exception as e:
        return 0, {}, str(e).encode("utf-8")


def main() -> int:
    target = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TARGET
    target = target.rstrip("/")
    print(f"Running Pre-show Health Check against: {target}\n")

    passed = 0
    failed = 0

    def check(name: str, condition: bool, detail: str = ""):
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  [PASS] {name} {f'({detail})' if detail else ''}")
        else:
            failed += 1
            print(f"  [FAIL] {name} {f'({detail})' if detail else ''}")

    # 1. Readiness Probe
    status, _, body = http_request(f"{target}/ready")
    build = ""
    try:
        data = json.loads(body.decode("utf-8"))
        build = data.get("build", "")
    except Exception:
        pass
    check("1. Readiness Probe (/ready)", status == 200 and bool(build), f"HTTP {status}, build={build}")

    # 2. Unauthenticated Access Defense
    status, _, _ = http_request(f"{target}/api/v1/instruments/")
    check("2. Unauthenticated Access Defense (/api/v1/instruments/)", status in (401, 403), f"HTTP {status}")

    # 3. Public Verify Receipt Page
    status, _, body = http_request(f"{target}/verify-receipt")
    check("3. Public Verify Route (/verify-receipt)", status == 200 and b"<html" in body.lower(), f"HTTP {status}")

    # 4. Demo Sample Receipt PDF
    status, headers, body = http_request(f"{target}/api/v1/demo/sample-receipt.pdf")
    is_pdf = body.startswith(b"%PDF-")
    sz = len(body)
    check(
        "4. Demo Sample Receipt PDF (/api/v1/demo/sample-receipt.pdf)",
        status == 200 and is_pdf and sz < 300_000,
        f"HTTP {status}, size={sz} bytes",
    )

    # 5. Sample Receipt Token Verification
    status, _, body = http_request(f"{target}/api/v1/demo/sample-receipt?format=token")
    token = ""
    if status == 200:
        try:
            token = json.loads(body.decode("utf-8")).get("token", "")
        except Exception:
            pass

    verify_valid = False
    if token:
        v_payload = json.dumps({"token": token}).encode("utf-8")
        v_status, _, v_body = http_request(
            f"{target}/api/v1/receipts/verify",
            method="POST",
            headers={"Content-Type": "application/json"},
            data=v_payload,
        )
        if v_status == 200:
            try:
                v_data = json.loads(v_body.decode("utf-8"))
                verify_valid = v_data.get("valid") is True
            except Exception:
                pass

    check("5. Sample Token Verification (/api/v1/receipts/verify)", verify_valid, f"valid={verify_valid}")

    # 6. Tampered Token Rejection
    tampered_rejected = False
    if token:
        tampered_token = token[:-1] + ("A" if token[-1] != "A" else "B")
        t_payload = json.dumps({"token": tampered_token}).encode("utf-8")
        t_status, _, t_body = http_request(
            f"{target}/api/v1/receipts/verify",
            method="POST",
            headers={"Content-Type": "application/json"},
            data=t_payload,
        )
        if t_status == 200:
            try:
                t_data = json.loads(t_body.decode("utf-8"))
                tampered_rejected = t_data.get("valid") is False
            except Exception:
                pass

    check("6. Tampered Token Rejection", tampered_rejected, "rejected bad signature")

    # 7. Security Headers Check
    status, headers, _ = http_request(f"{target}/")
    csp = "content-security-policy" in headers
    nosniff = headers.get("x-content-type-options") == "nosniff"
    xframe = "x-frame-options" in headers
    sec_ok = csp and nosniff and xframe
    check("7. Security Headers (CSP, nosniff, DENY)", sec_ok, f"csp={csp}, nosniff={nosniff}, xframe={xframe}")

    print("\n" + "=" * 50)
    print(f"Preshow Summary: {passed}/{passed + failed} checks passed")
    print("=" * 50)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
