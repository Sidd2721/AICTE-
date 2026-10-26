import json
from datetime import date
from pathlib import Path
from typing import Any

RULES_DIR = Path(__file__).resolve().parent.parent / "rules"


def load_rule(rules_dir: Path | None, name: str, on: date) -> dict[str, Any]:
    """Pick <name>.<YYYY-MM-DD>.json with the latest effective_from <= on."""
    target_dir = rules_dir or RULES_DIR
    best: tuple[date, dict[str, Any]] | None = None
    for p in target_dir.glob(f"{name}.*.json"):
        doc = json.loads(p.read_text(encoding="utf-8"))
        eff = date.fromisoformat(doc["effective_from"])
        if eff <= on and (best is None or eff > best[0]):
            best = (eff, doc)
    if best is None:
        raise LookupError(f"no rule '{name}' effective on {on}")
    return best[1]


def required_deposit_paise(
    programme_amounts_paise: list[int],
    leased_private: bool,
    rule: dict[str, Any],
    is_government: bool = False,
) -> int:
    """Sum across programmes; multiplier from rule (e.g. 2 for private leased); 0 if government exempt."""
    if is_government and rule.get("government_exempt", True):
        return 0
    mult = rule.get("leased_private_multiplier", 2) if leased_private else 1
    return sum(programme_amounts_paise) * mult


def calculate_institution_coverage(
    programme_amounts_paise: list[int],
    leased_private: bool,
    rule: dict[str, Any],
    is_government: bool,
    instruments: list[dict[str, Any]],
) -> dict[str, int]:
    """Computes statutory required, confirmed-active, claimed-only, and shortfall in paise.
    Shortfall = max(0, required - confirmed_active).
    """
    req = required_deposit_paise(
        programme_amounts_paise=programme_amounts_paise,
        leased_private=leased_private,
        rule=rule,
        is_government=is_government,
    )
    confirmed_active = 0
    claimed_only = 0
    for inst in instruments:
        amt = int(inst.get("amount_paise", 0))
        badge = str(inst.get("badge", "claimed")).lower()
        lifecycle = str(inst.get("lifecycle", "pending")).lower()
        if lifecycle in ("active", "pending"):
            if badge == "confirmed":
                confirmed_active += amt
            else:
                claimed_only += amt
    shortfall = max(0, req - confirmed_active)
    return {
        "required_paise": req,
        "confirmed_active_paise": confirmed_active,
        "claimed_only_paise": claimed_only,
        "shortfall_paise": shortfall,
    }


def startup_guard(rule_docs: list[dict[str, Any]], env: str | None) -> None:
    """Invariant I7: outside development/demo, refuse to start while any rule is not CONFIRMED."""
    if env in ("development", "demo"):
        return
    bad = [
        d.get("notes", "?")[:60] for d in rule_docs if d.get("status") != "CONFIRMED"
    ]
    if bad:
        raise RuntimeError(
            f"{len(bad)} rule file(s) are DEMO/placeholder; refusing to start outside development"
        )
