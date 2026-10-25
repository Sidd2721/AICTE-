import json
from datetime import date
from pathlib import Path

def load_rule(rules_dir: Path, name: str, on: date) -> dict:
    """Pick <name>.<YYYY-MM-DD>.json with the latest effective_from <= on."""
    best = None
    for p in rules_dir.glob(f"{name}.*.json"):
        doc = json.loads(p.read_text())
        eff = date.fromisoformat(doc["effective_from"])
        if eff <= on and (best is None or eff > best[0]):
            best = (eff, doc)
    if best is None:
        raise LookupError(f"no rule '{name}' effective on {on}")
    return best[1]

def required_deposit_paise(programme_amounts_paise: list[int], leased_private: bool, rule: dict) -> int:
    """Sum across programmes; multiplier from rule (e.g. 2 for private leased)."""
    mult = rule["leased_private_multiplier"] if leased_private else 1
    return sum(programme_amounts_paise) * mult


def startup_guard(rule_docs: list[dict], env: str) -> None:
    """Invariant I7: outside development, refuse to start while any rule is not CONFIRMED."""
    if env == "development":
        return
    bad = [d.get("notes", "?")[:60] for d in rule_docs if d.get("status") != "CONFIRMED"]
    if bad:
        raise RuntimeError(f"{len(bad)} rule file(s) are DEMO/placeholder; refusing to start outside development")
