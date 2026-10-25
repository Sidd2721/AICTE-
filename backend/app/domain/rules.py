import json
from datetime import date
from pathlib import Path
from typing import Any, cast


def load_rule(rules_dir: Path, name: str, on: date) -> dict[str, Any]:
    """Pick <name>.<YYYY-MM-DD>.json with the latest effective_from <= on."""
    best: tuple[date, dict[str, Any]] | None = None
    for p in rules_dir.glob(f"{name}.*.json"):
        doc = cast(dict[str, Any], json.loads(p.read_text(encoding="utf-8")))
        eff = date.fromisoformat(str(doc["effective_from"]))
        if eff <= on and (best is None or eff > best[0]):
            best = (eff, doc)
    if best is None:
        raise LookupError(f"no rule '{name}' effective on {on}")
    return best[1]


def required_deposit_paise(
    programme_amounts_paise: list[int], leased_private: bool, rule: dict[str, Any]
) -> int:
    """Sum across programmes; multiplier from rule (e.g. 2 for private leased)."""
    mult = int(rule["leased_private_multiplier"]) if leased_private else 1
    return sum(programme_amounts_paise) * mult


def startup_guard(rule_docs: list[dict[str, Any]], env: str) -> None:
    """Invariant I7: in production, refuse to start while any rule is not CONFIRMED."""
    if env in ("development", "demo"):
        return
    bad = [
        str(d.get("notes", "?"))[:60]
        for d in rule_docs
        if d.get("status") != "CONFIRMED"
    ]
    if bad:
        raise RuntimeError(
            f"{len(bad)} rule file(s) are DEMO/placeholder; refusing to start outside development"
        )
