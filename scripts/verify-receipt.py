#!/usr/bin/env python3
"""Offline Release Receipt Verifier (AICTE PS 26265)

Verifies a PyJWT release receipt token offline using only the RSA public key.
Zero database connection required.
"""
import argparse
import json
import sys
from pathlib import Path

import jwt

DEFAULT_PUBLIC_KEY = Path(__file__).parent.parent / "backend" / "app" / "keys" / "receipt_public.pem"


def verify_receipt(token: str, public_key_path: Path | None = None) -> dict:
    key_path = public_key_path or DEFAULT_PUBLIC_KEY
    if not key_path.exists():
        raise FileNotFoundError(f"Public key not found at {key_path}")

    pub_bytes = key_path.read_bytes()
    decoded = jwt.decode(
        token,
        pub_bytes,
        algorithms=["RS256"],
        options={"require": ["receipt_id", "iat", "instrument_hash", "path"]},
    )
    return decoded


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify an AICTE Release Receipt Token offline.")
    parser.add_argument("--token", required=True, help="JWT token string of the release receipt")
    parser.add_argument("--public-key", type=Path, default=None, help="Path to receipt_public.pem")
    args = parser.parse_args()

    try:
        claims = verify_receipt(args.token, args.public_key)
        print("STATUS: VALID")
        print("CLAIMS:")
        print(json.dumps(claims, indent=2))
        sys.exit(0)
    except Exception as e:
        print(f"STATUS: INVALID ({e})", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
