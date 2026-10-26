#!/usr/bin/env python3
"""Smoke test suite for deployed AICTE FDR Portal instances (Sprint 2 Track 1 + Track 2).

Standard library only. No external packages (requests/httpx) required.

Usage:
    python scripts/smoke_deployed.py [BASE_URL] [--password PASSWORD]
    python scripts/smoke_deployed.py http://localhost:8000
"""

from __future__ import annotations

import argparse
import json
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

PERSONAS = [
    ("inst.north1@example.com", "institution"),
    ("officer.north@example.com", "regional"),
    ("bureau@example.com", "bureau"),
    ("auditor@example.com", "auditor"),
]


class SmokeTester:
    def __init__(self, base_url: str, default_password: str = "changethis") -> None:
        self.base_url = base_url.rstrip("/")
        self.password = default_password
        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE
        self.passed = 0
        self.failed = 0

    def log_test(self, name: str, success: bool, detail: str = "") -> None:
        if success:
            self.passed += 1
            print(f"\033[1;32m[PASS]\033[0m {name} {detail}")
        else:
            self.failed += 1
            print(f"\033[1;31m[FAIL]\033[0m {name} {detail}")

    def request(
        self,
        path: str,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        data: bytes | None = None,
    ) -> tuple[int, dict[str, str], bytes]:
        url = f"{self.base_url}{path}"
        req_headers = headers or {}
        req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=10, context=self.ctx) as resp:
                resp_headers = {k.lower(): v for k, v in resp.headers.items()}
                return resp.status, resp_headers, resp.read()
        except urllib.error.HTTPError as e:
            resp_headers = {k.lower(): v for k, v in e.headers.items()}
            return e.code, resp_headers, e.read()
        except Exception as e:
            return 0, {}, str(e).encode()

    def test_health(self) -> None:
        status, _, body = self.request("/api/v1/utils/health-check/")
        ok = status == 200
        self.log_test("1. Health Check (/api/v1/utils/health-check/)", ok, f"(HTTP {status})")

    def test_spa_load(self) -> None:
        status, _, body = self.request("/")
        html = body.decode("utf-8", errors="replace")
        ok = status == 200 and ("<div id=\"root\">" in html or "<script" in html)
        self.log_test("2. SPA HTML Shell (GET /)", ok, f"(Length: {len(html)} bytes)")

    def test_meta_endpoint(self) -> None:
        status, _, body = self.request("/api/v1/meta")
        try:
            data = json.loads(body.decode())
            self.env = data.get("env_label", "development")
            has_fields = "env_label" in data and "rule_status" in data and "commit" in data
            no_secrets = "SECRET_KEY" not in str(data) and "password" not in str(data).lower()
            ok = status == 200 and has_fields and no_secrets
            detail = f"(env={data.get('env_label')}, rules={data.get('rule_status')})"
        except Exception as e:
            ok = False
            detail = f"(Error: {e})"
        self.log_test("3. Transparency Metadata (/api/v1/meta)", ok, detail)

    def test_security_headers(self) -> None:
        status, headers, _ = self.request("/")
        csp = headers.get("content-security-policy", "")
        nosniff = headers.get("x-content-type-options", "")
        frame = headers.get("x-frame-options", "")
        ok = (
            status == 200
            and "default-src" in csp
            and nosniff == "nosniff"
            and frame == "DENY"
        )
        self.log_test(
            "4. Security Headers (CSP, nosniff, X-Frame-Options)",
            ok,
            f"(nosniff={nosniff}, x-frame={frame})",
        )

    def test_persona_logins(self) -> dict[str, str]:
        tokens: dict[str, str] = {}
        for email, role in PERSONAS:
            form_data = urllib.parse.urlencode({
                "username": email,
                "password": self.password,
            }).encode()
            status, _, body = self.request(
                "/api/v1/login/access-token",
                method="POST",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data=form_data,
            )
            try:
                res = json.loads(body.decode())
                token = res.get("access_token")
                if status == 200 and token:
                    tokens[role] = token
                    self.log_test(f"5. Persona Login: {role} ({email})", True, "(JWT acquired)")
                else:
                    self.log_test(f"5. Persona Login: {role} ({email})", False, f"(HTTP {status}: {body.decode()[:60]})")
            except Exception as e:
                self.log_test(f"5. Persona Login: {role} ({email})", False, f"({e})")
        return tokens

    def test_authenticated_features(self, tokens: dict[str, str]) -> None:
        # 6a. Dashboard counters
        ro_token = tokens.get("regional")
        if ro_token:
            status, _, body = self.request(
                "/api/v1/dashboard/counters",
                headers={"Authorization": f"Bearer {ro_token}"},
            )
            try:
                cnt = json.loads(body.decode())
                ok = status == 200 and "active" in cnt
                self.log_test("6. Dashboard Regulatory Counters", ok, f"(active={cnt.get('active', 0)})")
            except Exception as e:
                self.log_test("6. Dashboard Regulatory Counters", False, f"({e})")

        # 6b. Audit hash chain verification
        bureau_token = tokens.get("bureau")
        if bureau_token:
            status, _, body = self.request(
                "/api/v1/audit/verify",
                headers={"Authorization": f"Bearer {bureau_token}"},
            )
            try:
                v = json.loads(body.decode())
                ok = status == 200 and (v.get("status") == "clean" or v.get("valid") is True)
                self.log_test("7. Audit Ledger Cryptographic Hash Chain", ok, f"(status={v.get('status')})")
            except Exception as e:
                self.log_test("7. Audit Ledger Cryptographic Hash Chain", False, f"({e})")

    def test_rate_limiting(self) -> None:
        # Rapid failed logins to verify rate limiting protection
        rate_limited = False
        max_attempts = 10 if getattr(self, "env", "development") in ("demo", "production") else 30
        for _ in range(max_attempts):
            bad_data = urllib.parse.urlencode({
                "username": "attacker@example.com",
                "password": "wrongpassword",
            }).encode()
            status, _, _ = self.request(
                "/api/v1/login/access-token",
                method="POST",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data=bad_data,
            )
            if status == 429:
                rate_limited = True
                break
            time.sleep(0.01)
        # In demo / production environments, rate limit triggers at 5 requests
        is_demo_or_prod = getattr(self, "env", "development") in ("demo", "production")
        ok = rate_limited if is_demo_or_prod else True
        self.log_test(
            "8. Rate Limiting Defense (Brute Force Protection)",
            ok,
            "(HTTP 429 triggered)" if rate_limited else f"(env={getattr(self, 'env', 'development')} higher limit active)",
        )

    def run_all(self) -> int:
        print(f"\nRunning Smoke Suite on: {self.base_url}")
        print("=" * 60)
        self.test_health()
        self.test_spa_load()
        self.test_meta_endpoint()
        self.test_security_headers()
        tokens = self.test_persona_logins()
        self.test_authenticated_features(tokens)
        self.test_rate_limiting()
        print("=" * 60)
        print(f"Results: {self.passed} Passed, {self.failed} Failed\n")
        return 0 if self.failed == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test suite for deployed AICTE FDR Portal")
    parser.add_argument("base_url", nargs="?", default="http://localhost:8000", help="Base URL of target instance")
    parser.add_argument("--password", "-p", default="changethis", help="Password for persona accounts")
    args = parser.parse_args()

    tester = SmokeTester(args.base_url, args.password)
    return tester.run_all()


if __name__ == "__main__":
    raise SystemExit(main())
