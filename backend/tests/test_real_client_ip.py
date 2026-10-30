"""Tests for client IP extraction and rate-limit proxy spoofing defense (FT2).

Source: Render Documentation (https://render.com/docs/web-services#client-ip-address)
Render terminates TLS and appends the client IP to X-Forwarded-For and injects True-Client-IP.
"""
from fastapi import Request
from sqlmodel import Session
from starlette.datastructures import Headers

from app.core.db import engine
from app.core.rate_limit import check_rate_limit, ensure_rate_limit_table, get_client_ip


def make_mock_request(headers_dict: dict[str, str], client_host: str = "10.0.0.1") -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/integration/v1/bank/requests/pending",
        "headers": [(k.lower().encode("latin-1"), v.encode("latin-1")) for k, v in headers_dict.items()],
        "client": (client_host, 12345),
    }
    return Request(scope)


def test_client_ip_zero_hops_legacy():
    """Default TRUSTED_PROXY_HOPS=0 retains legacy behavior (first XFF or socket)."""
    req = make_mock_request({"X-Forwarded-For": "198.51.100.1, 10.0.0.1"})
    ip = get_client_ip(req, trusted_hops=0)
    assert ip == "198.51.100.1"

    req_no_header = make_mock_request({}, client_host="192.168.1.50")
    ip_direct = get_client_ip(req_no_header, trusted_hops=0)
    assert ip_direct == "192.168.1.50"


def test_client_ip_render_true_client_ip():
    """Render sets True-Client-IP containing the verified client public IP."""
    req = make_mock_request({
        "True-Client-IP": "203.0.113.42",
        "X-Forwarded-For": "1.1.1.1, 203.0.113.42",
    })
    ip = get_client_ip(req, trusted_hops=1)
    assert ip == "203.0.113.42"


def test_forged_header_does_not_bypass_limit():
    """An attacker varying the forged leading XFF header cannot evade rate limits."""
    real_ip = "203.0.113.99"
    with Session(engine) as session:
        ensure_rate_limit_table(session)
        # Attempt 1: attacker claims to be 1.1.1.1
        req1 = make_mock_request({"X-Forwarded-For": f"1.1.1.1, {real_ip}"})
        ip1 = get_client_ip(req1, trusted_hops=1)
        assert ip1 == real_ip

        key = f"rl:test_forgery:{ip1}"
        allowed1, _ = check_rate_limit(session, key=key, max_requests=2, window_seconds=60)
        assert allowed1 is True

        # Attempt 2: attacker changes forged header to 2.2.2.2
        req2 = make_mock_request({"X-Forwarded-For": f"2.2.2.2, {real_ip}"})
        ip2 = get_client_ip(req2, trusted_hops=1)
        assert ip2 == real_ip

        allowed2, _ = check_rate_limit(session, key=key, max_requests=2, window_seconds=60)
        assert allowed2 is True

        # Attempt 3: attacker changes forged header to 3.3.3.3 -> must be blocked
        req3 = make_mock_request({"X-Forwarded-For": f"3.3.3.3, {real_ip}"})
        ip3 = get_client_ip(req3, trusted_hops=1)
        assert ip3 == real_ip

        allowed3, retry_after = check_rate_limit(session, key=key, max_requests=2, window_seconds=60)
        assert allowed3 is False
        assert retry_after > 0


def test_two_different_clients_counted_separately():
    """Two distinct client IPs maintain independent rate-limit quotas."""
    client_a = "198.51.100.10"
    client_b = "198.51.100.20"

    with Session(engine) as session:
        ensure_rate_limit_table(session)
        key_a = f"rl:test_iso:{client_a}"
        key_b = f"rl:test_iso:{client_b}"

        # Exhaust client A
        check_rate_limit(session, key=key_a, max_requests=1, window_seconds=60)
        allowed_a, _ = check_rate_limit(session, key=key_a, max_requests=1, window_seconds=60)
        assert allowed_a is False

        # Client B must remain unaffected
        allowed_b, _ = check_rate_limit(session, key=key_b, max_requests=1, window_seconds=60)
        assert allowed_b is True
