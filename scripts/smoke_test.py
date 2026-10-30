#!/usr/bin/env python3
"""Cross-platform smoke test runner for AICTE FDR Portal deployments (FT6).

Verifies liveness, readiness, persona authentication, role-scoped data endpoints,
cryptographic audit chain continuity, and API documentation route gating.
Uses only Python standard library and synthetic demo credentials.
"""
# ruff: noqa: T201
import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

ROLES = [
    ("Technical Institution", "inst.north1@example.com", "/api/v1/instruments/?limit=5"),
    ("Regional Officer (Maker)", "officer.north@example.com", "/api/v1/instruments/?limit=5"),
    ("Scrutiny Checker", "checker.north@example.com", "/api/v1/instruments/?limit=5"),
    ("Bureau Approver", "bureau@example.com", "/api/v1/dashboard/counters"),
    ("Compliance Auditor", "auditor@example.com", "/api/v1/audit/events?limit=5"),
]

DEFAULT_PASSWORD = "AdminSecure2026!"
DEFAULT_BASE_URL = "https://aicte-1-59pn.onrender.com"

# ANSI color codes
COLOR_GREEN = "\033[92m"
COLOR_RED = "\033[91m"
COLOR_CYAN = "\033[96m"
COLOR_RESET = "\033[0m"


def make_request(
    url: str,
    method: str = "GET",
    data: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 30.0,
) -> tuple[int, Any, float]:
    """Perform HTTP request, returning (status_code, response_body, elapsed_seconds)."""
    headers = headers or {}
    encoded_data = None
    if data is not None:
        if headers.get("Content-Type") == "application/x-www-form-urlencoded":
            encoded_data = urllib.parse.urlencode(data).encode("utf-8")
        else:
            headers["Content-Type"] = "application/json"
            encoded_data = json.dumps(data).encode("utf-8")

    req = urllib.request.Request(url, data=encoded_data, headers=headers, method=method)
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            elapsed = time.perf_counter() - t0
            body_bytes = resp.read()
            try:
                body = json.loads(body_bytes.decode("utf-8"))
            except Exception:
                body = body_bytes.decode("utf-8", errors="replace")
            return resp.status, body, elapsed
    except urllib.error.HTTPError as e:
        elapsed = time.perf_counter() - t0
        err_bytes = e.read()
        try:
            err_body = json.loads(err_bytes.decode("utf-8"))
        except Exception:
            err_body = err_bytes.decode("utf-8", errors="replace")
        return e.code, err_body, elapsed
    except Exception as e:
        elapsed = time.perf_counter() - t0
        return 0, str(e), elapsed


def run_smoke_checks(base_url: str, password: str, expect_docs_hidden: bool) -> list[dict[str, Any]]:
    base_url = base_url.rstrip("/")
    results: list[dict[str, Any]] = []

    def record(name: str, passed: bool, duration: float, detail: str = ""):
        results.append({
            "check": name,
            "status": "PASS" if passed else "FAIL",
            "duration": f"{duration:.3f}s",
            "detail": detail,
        })

    # 1. Liveness Probe
    code, body, dur = make_request(f"{base_url}/health")
    ok = code == 200 and isinstance(body, dict) and body.get("status") == "ok"
    record("1. Liveness (/health)", ok, dur, f"HTTP {code}")

    # 2. Readiness Probe
    code, body, dur = make_request(f"{base_url}/ready")
    ok = code == 200 and isinstance(body, dict) and body.get("status") == "ready"
    record("2. Readiness (/ready)", ok, dur, f"HTTP {code}")

    # 3. Role Authentication and Scoped List Endpoints
    for role_name, email, list_path in ROLES:
        auth_data = {"username": email, "password": password}
        code, body, dur = make_request(
            f"{base_url}/api/v1/login/access-token",
            method="POST",
            data=auth_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        token = body.get("access_token") if isinstance(body, dict) else None
        auth_ok = code == 200 and bool(token)
        record(f"3. Login: {role_name}", auth_ok, dur, f"HTTP {code}")

        if auth_ok and token:
            l_code, l_body, l_dur = make_request(
                f"{base_url}{list_path}",
                headers={"Authorization": f"Bearer {token}"},
            )
            list_ok = l_code == 200
            record(f"4. Scoped List: {role_name}", list_ok, l_dur, f"HTTP {l_code} on {list_path}")
        else:
            record(f"4. Scoped List: {role_name}", False, 0.0, "Skipped due to login failure")

    # 5. Audit Hash Chain Verification
    # Use auditor token or superuser
    code, body, dur = make_request(
        f"{base_url}/api/v1/login/access-token",
        method="POST",
        data={"username": "auditor@example.com", "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token = body.get("access_token") if isinstance(body, dict) else None
    if token:
        v_code, v_body, v_dur = make_request(
            f"{base_url}/api/v1/audit/verify",
            headers={"Authorization": f"Bearer {token}"},
        )
        status_field = v_body.get("status") if isinstance(v_body, dict) else None
        v_ok = v_code == 200 and isinstance(v_body, dict) and status_field == "clean"
        record(
            "5. Audit Chain Integrity",
            v_ok,
            v_dur,
            f"Status: {status_field} (HTTP {v_code})",
        )
    else:
        record("5. Audit Chain Integrity", False, 0.0, "Auditor token missing")

    # 6. Documentation Gating (/docs, /redoc, /api/v1/openapi.json)
    for doc_path in ("/docs", "/redoc", "/api/v1/openapi.json"):
        code, _, dur = make_request(f"{base_url}{doc_path}")
        if expect_docs_hidden:
            doc_ok = code == 404
            record(f"6. Docs Gating: {doc_path}", doc_ok, dur, f"HTTP {code} (Expected 404)")
        else:
            doc_ok = code in (200, 404)
            record(f"6. Docs Accessible: {doc_path}", doc_ok, dur, f"HTTP {code}")

    return results


def print_table(results: list[dict[str, Any]]) -> bool:
    print("\n" + "=" * 82)
    print(f"           {COLOR_CYAN}AICTE FDR PORTAL - SMOKE VERIFICATION SUITE{COLOR_RESET}")
    print("=" * 82)
    print(f"{'Check Description':<40} | {'Status':<6} | {'Time':<8} | {'Details'}")
    print("-" * 82)
    all_passed = True
    for r in results:
        is_pass = r["status"] == "PASS"
        if not is_pass:
            all_passed = False
        color = COLOR_GREEN if is_pass else COLOR_RED
        status_colored = f"{color}{r['status']:<6}{COLOR_RESET}"
        print(f"{r['check']:<40} | {status_colored} | {r['duration']:<8} | {r['detail']}")
    print("=" * 82)
    if all_passed:
        print(f"RESULT: {COLOR_GREEN}ALL SMOKE CHECKS PASSED [GREEN]{COLOR_RESET}\n")
    else:
        print(f"RESULT: {COLOR_RED}ONE OR MORE CHECKS FAILED [RED]{COLOR_RESET}\n")
    return all_passed


def main() -> int:
    parser = argparse.ArgumentParser(description="Run smoke test against an AICTE FDR Portal URL.")
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"Base URL of application (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument("--password", default=DEFAULT_PASSWORD, help="Default persona password")
    parser.add_argument(
        "--expect-docs-hidden",
        action="store_true",
        help="Expect /docs to return 404 (production/demo mode)",
    )
    args = parser.parse_args()

    target_url = args.base_url
    if not target_url.startswith("http://") and not target_url.startswith("https://"):
        target_url = f"https://{target_url}"

    print(f"Targeting deployment at: {target_url}")
    results = run_smoke_checks(target_url, args.password, args.expect_docs_hidden)
    passed = print_table(results)
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
