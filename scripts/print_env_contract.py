#!/usr/bin/env python3
"""Print the REAL environment-variable contract of the backend, straight from its source.

Run from the repo root:   python scripts/print_env_contract.py [path/to/backend/app]
It reads `class Settings` in app/core/config.py with the AST (no imports, no secrets needed) and
scans the code for os.environ / os.getenv usage, so the list can never drift from the code.
Exit code 1 if code reads an environment variable that is not declared in Settings."""
import ast
import re
import sys
from pathlib import Path

app_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("backend/app")
cfg = app_dir / "core" / "config.py"
if not cfg.exists():
    sys.exit(f"cannot find {cfg}; pass the path to your backend/app directory")

SECRETISH = re.compile(r"(SECRET|PASSWORD|KEY|TOKEN|DSN|DATABASE_URL|PRIVATE|SALT)", re.I)
NOT_SECRET = re.compile(r"(EXPIRE|MINUTES|HOURS|DAYS|TIMEOUT)", re.I)

tree = ast.parse(cfg.read_text())
settings_cls = next((n for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and n.name == "Settings"), None)
if settings_cls is None:
    sys.exit("no `class Settings` found in config.py")

fields: dict[str, dict[str, str]] = {}
for node in settings_cls.body:
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        name = node.target.id
        if name == "model_config" or name.startswith("_"):
            continue
        ann = ast.unparse(node.annotation)
        if "ClassVar" in ann:
            continue
        has_default = node.value is not None
        default = ast.unparse(node.value) if has_default else ""
        fields[name] = {"type": ann, "default": default, "required": "NO" if has_default else "YES"}

# env reads outside Settings
env_reads: dict[str, list[str]] = {}
for py in app_dir.rglob("*.py"):
    try:
        t = ast.parse(py.read_text())
    except SyntaxError:
        continue
    for n in ast.walk(t):
        key = None
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in {"get", "getenv"} and n.args:
            base = ast.unparse(n.func.value)
            if base in {"os.environ", "os", "environ"} and isinstance(n.args[0], ast.Constant):
                key = n.args[0].value
        if isinstance(n, ast.Subscript) and ast.unparse(n.value) in {"os.environ", "environ"} and isinstance(n.slice, ast.Constant):
            key = n.slice.value
        if isinstance(key, str):
            env_reads.setdefault(key, []).append(str(py.relative_to(app_dir)))

print("| Variable | Required | Secret? | Type | Default in code |")
print("|---|---|---|---|---|")
for name, f in fields.items():
    secret = "yes" if SECRETISH.search(name) and not NOT_SECRET.search(name) else ""
    default = "(none)" if f["required"] == "YES" else ("`" + ("***" if secret and f["default"] not in ("None", "''", '""') else f["default"]) + "`")
    print(f"| `{name}` | {f['required']} | {secret} | `{f['type']}` | {default} |")

undeclared = {k: v for k, v in env_reads.items() if k not in fields and k.upper() not in {n.upper() for n in fields}}
if undeclared:
    print("\nEnvironment variables read directly in code but NOT declared in Settings:")
    for k, files in sorted(undeclared.items()):
        print(f"- `{k}` (in {', '.join(sorted(set(files)))})")
    sys.exit(1)
print(f"\n{len(fields)} settings; {sum(1 for f in fields.values() if f['required']=='YES')} required; no undeclared os.environ reads.")
