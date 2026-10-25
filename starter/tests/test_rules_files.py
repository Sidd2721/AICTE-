from datetime import date
from pathlib import Path
import pytest
from rules import load_rule, required_deposit_paise, startup_guard

RULES = Path(__file__).resolve().parents[1] / "rules"
NAMES = ["deposit", "timelines", "release_paths"]

@pytest.mark.parametrize("name", NAMES)
def test_rule_file_loads_and_is_marked(name):
    doc = load_rule(RULES, name, date(2026, 11, 1))
    assert doc["status"] in {"DEMO", "CONFIRMED"} and doc["effective_from"] == "2024-04-01"

def test_deposit_sum_and_double_with_demo_values():
    rule = load_rule(RULES, "deposit", date(2026, 11, 1))
    amounts = list(rule["programme_amounts_paise"].values())
    assert required_deposit_paise(amounts, False, rule) == 80_000_000
    assert required_deposit_paise(amounts, True, rule) == 160_000_000

def test_release_paths_have_the_four_paths_and_every_item_has_a_source():
    doc = load_rule(RULES, "release_paths", date(2026, 11, 1))
    assert set(doc["paths"]) == {"term_completion", "closure", "merger", "conversion"}
    for path in doc["paths"].values():
        assert all(i["source"] for i in path["checklist"])
    assert any(i["id"] == "no_pending_complaints" for i in doc["paths"]["conversion"]["checklist"])
    assert not any(i["id"] == "no_pending_complaints" for i in doc["paths"]["closure"]["checklist"])

def test_guard_blocks_demo_rules_outside_development():
    docs = [load_rule(RULES, n, date(2026, 11, 1)) for n in NAMES]
    startup_guard(docs, "development")
    with pytest.raises(RuntimeError):
        startup_guard(docs, "production")
    startup_guard([{**d, "status": "CONFIRMED"} for d in docs], "production")
