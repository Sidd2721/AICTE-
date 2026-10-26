#!/usr/bin/env python3
"""Offline Release Receipt Verifier (AICTE PS 26265) <= 40 lines"""
import argparse, json, sys
from pathlib import Path
import jwt

DEFAULT_KEY = Path(__file__).parent.parent / "backend" / "app" / "keys" / "receipt_public.pem"

def verify(token: str, key_path: Path = DEFAULT_KEY) -> dict:
    return jwt.decode(token, key_path.read_bytes(), algorithms=["RS256"], options={"require": ["receipt_id", "iat"]})

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--token", required=True)
    p.add_argument("--public-key", type=Path, default=DEFAULT_KEY)
    args = p.parse_args()
    try:
        claims = verify(args.token, args.public_key)
        print("STATUS: VALID\n" + json.dumps(claims, indent=2))
    except Exception as e:
        print(f"STATUS: INVALID ({e})", file=sys.stderr)
        sys.exit(1)
