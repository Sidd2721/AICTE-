#!/usr/bin/env python3
"""Generates cryptographically random secrets for demo and production deployments (Sprint 2 Track 2).

Usage:
    python scripts/gen_secrets.py [--output deploy/.env.demo]
"""

from __future__ import annotations

import argparse
import base64
import secrets
import sys
from pathlib import Path


def generate_secrets() -> dict[str, str]:
    return {
        "SECRET_KEY": secrets.token_urlsafe(32),
        "VAULT_KEY": base64.b64encode(secrets.token_bytes(32)).decode(),
        "POSTGRES_PASSWORD": secrets.token_urlsafe(24),
        "FIRST_SUPERUSER_PASSWORD": secrets.token_urlsafe(24),
    }


def render_env(sec: dict[str, str], domain: str = "localhost") -> str:
    return f"""# AICTE FDR Portal Demo Environment Configuration (Track 2)
# Generated automatically by scripts/gen_secrets.py
FASTAPI_ENV=demo
PROJECT_NAME="AICTE Security Deposit / FDR Portal (DEMO)"
DOMAIN={domain}

# Cryptographic Keys (guarded against default/weak values in demo & production)
SECRET_KEY={sec["SECRET_KEY"]}
VAULT_KEY={sec["VAULT_KEY"]}

# Database Credentials
POSTGRES_USER=postgres
POSTGRES_PASSWORD={sec["POSTGRES_PASSWORD"]}
POSTGRES_DB=app

# Initial Administrator Account
FIRST_SUPERUSER=admin@example.com
FIRST_SUPERUSER_PASSWORD={sec["FIRST_SUPERUSER_PASSWORD"]}

# Email & Notifications (Mailpit simulated SMTP)
SMTP_HOST=mailpit
SMTP_PORT=1025
EMAILS_FROM_EMAIL=noreply@fdr.aicte-india.org
EMAILS_FROM_NAME="AICTE FDR Regulatory System"
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate production-grade secrets for demo deployment")
    parser.add_argument("--output", "-o", type=Path, default=None, help="Path to write the generated .env file")
    parser.add_argument("--domain", "-d", type=str, default="localhost", help="Domain name for TLS routing")
    args = parser.parse_args()

    sec = generate_secrets()
    rendered = render_env(sec, args.domain)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(f"[OK] Generated secure deployment environment file at: {args.output}")
    else:
        sys.stdout.write(rendered)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
