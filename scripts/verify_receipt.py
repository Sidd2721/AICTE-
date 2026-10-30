#!/usr/bin/env python3
"""Offline & Live Release Receipt Verifier (AICTE PS 26265).

Lightweight verification CLI tool relying exclusively on standard library
and PyJWT / cryptography (zero application imports).
Validates signed RS256 receipt tokens against AICTE's public verification key.
Pins algorithm strictly to RS256. Exits 0 on VALID, 1 on INVALID.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import urllib.error
import urllib.request
import jwt

DEFAULT_LOCAL_KEY = (
    Path(__file__).resolve().parent.parent
    / "backend"
    / "app"
    / "keys"
    / "receipt_public.pem"
)
DEFAULT_PUBLIC_URL = "https://aicte-1-59pn.onrender.com"


def fetch_public_key_pem(base_url: str) -> str:
    """Fetch the active RS256 public key PEM from the public endpoint."""
    url = f"{base_url.rstrip('/')}/api/v1/receipts/public-key"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "AICTE-Receipt-Verifier/1.0", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        pem = data.get("public_key_pem")
        if not pem:
            raise ValueError(f"Endpoint {url} did not return 'public_key_pem'")
        return str(pem)


def resolve_public_key(key_arg: str | None, base_url: str | None) -> str:
    """Resolve the public key from a file path, raw PEM string, or remote endpoint."""
    if key_arg:
        p = Path(key_arg)
        if p.exists() and p.is_file():
            return p.read_text(encoding="utf-8")
        if "BEGIN PUBLIC KEY" in key_arg:
            return key_arg
        raise FileNotFoundError(f"Key file not found: {key_arg}")

    if base_url:
        return fetch_public_key_pem(base_url)

    if DEFAULT_LOCAL_KEY.exists():
        return DEFAULT_LOCAL_KEY.read_text(encoding="utf-8")

    return fetch_public_key_pem(DEFAULT_PUBLIC_URL)


def verify_token(token: str, public_key_pem: str) -> dict:
    """Verify receipt token with pinned RS256 algorithm and required claims."""
    key_bytes = (
        public_key_pem.encode("utf-8")
        if isinstance(public_key_pem, str)
        else public_key_pem
    )
    return jwt.decode(
        token.strip(),
        key_bytes,
        algorithms=["RS256"],
        options={"require": ["receipt_id", "iat"]},
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify an AICTE release receipt token offline or via live public key.",
    )
    parser.add_argument(
        "token_pos",
        nargs="?",
        help="JWT token string (positional argument)",
    )
    parser.add_argument(
        "--token",
        dest="token_opt",
        help="JWT token string (flag argument)",
    )
    parser.add_argument(
        "--key",
        "--public-key",
        dest="key",
        help="Path to public key PEM file, or raw PEM string",
    )
    parser.add_argument(
        "--url",
        dest="url",
        help="Base URL of deployed backend to fetch public key from (e.g. https://aicte-1-59pn.onrender.com)",
    )

    args = parser.parse_args()
    token = args.token_opt or args.token_pos
    if not token:
        parser.error(
            "A token must be provided either as a positional argument or with --token"
        )

    try:
        pub_key = resolve_public_key(args.key, args.url)
        claims = verify_token(token, pub_key)
        print("STATUS: VALID")
        print(json.dumps(claims, indent=2))
        return 0
    except Exception as exc:
        print(f"STATUS: INVALID ({exc})", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
