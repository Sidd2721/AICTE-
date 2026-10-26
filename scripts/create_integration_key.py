#!/usr/bin/env python3
"""Create a scoped machine key and print the secret once."""

import argparse

from app.core.db import engine
from app.integration.apikeys import issue_api_key
from sqlmodel import Session


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a scoped FDR integration API key")
    parser.add_argument("client_name")
    parser.add_argument("scopes", nargs="+", choices=["coverage:read", "institutions:write", "events:subscribe"])
    args = parser.parse_args()
    raw_key, record = issue_api_key(args.client_name, set(args.scopes))
    with Session(engine) as session:
        session.add(record)
        session.commit()
    print("Store this key securely; it cannot be displayed again:")
    print(raw_key)


if __name__ == "__main__":
    main()
