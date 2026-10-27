#!/usr/bin/env python3
"""Generate and drift-check docs/openapi-integration.json.

Requirement 3.4: docs/openapi-integration.json generated and drift-checked.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add backend to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.main import app


def build_integration_spec() -> dict:
    full_spec = app.openapi()
    integration_paths = {
        k: v for k, v in full_spec.get("paths", {}).items() if k.startswith("/api/integration/v1")
    }

    # Collect referenced schemas
    used_schemas: set[str] = set()

    def find_refs(obj: object) -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == "$ref" and isinstance(v, str) and v.startswith("#/components/schemas/"):
                    used_schemas.add(v.split("/")[-1])
                else:
                    find_refs(v)
        elif isinstance(obj, list):
            for item in obj:
                find_refs(item)

    find_refs(integration_paths)

    all_schemas = full_spec.get("components", {}).get("schemas", {})
    # Transitively find any nested refs
    prev_count = 0
    while len(used_schemas) > prev_count:
        prev_count = len(used_schemas)
        for s in list(used_schemas):
            if s in all_schemas:
                find_refs(all_schemas[s])

    integration_spec = {
        "openapi": full_spec.get("openapi", "3.1.0"),
        "info": {
            "title": "AICTE Fixed Deposit Portal — Machine Integration API",
            "version": "1.0.0",
            "description": "Integration API for Core Banking Systems, SFMS adapters, and AICTE Central IT.",
        },
        "paths": integration_paths,
        "components": {
            "schemas": {k: all_schemas[k] for k in sorted(used_schemas) if k in all_schemas},
            "securitySchemes": {
                "ApiKeyAuth": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-API-Key",
                    "description": "Machine integration key issued by Bureau Officer",
                }
            },
        },
        "security": [{"ApiKeyAuth": []}],
    }
    return integration_spec


def main() -> None:
    output_path = ROOT_DIR / "docs" / "openapi-integration.json"
    spec = build_integration_spec()
    rendered = json.dumps(spec, indent=2, sort_keys=True) + "\n"

    check_only = "--check" in sys.argv
    if check_only:
        if not output_path.exists():
            print(f"Error: {output_path} does not exist.", file=sys.stderr)
            sys.exit(1)
        current = output_path.read_text(encoding="utf-8")
        if current.strip() != rendered.strip():
            print("Error: docs/openapi-integration.json is out of date. Run python scripts/generate_integration_openapi.py", file=sys.stderr)
            sys.exit(1)
        print("OK: docs/openapi-integration.json is up-to-date (no drift).")
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
        print(f"Wrote integration OpenAPI contract to {output_path}")


if __name__ == "__main__":
    main()
