from datetime import date
from pathlib import Path
import pytest

from app.domain.rules import load_rule, required_deposit_paise, startup_guard

RULES = Path(__file__).resolve().parents[1] / "app" / "rules"
NAMES = ["deposit", "timelines", "release_paths"]


@pytest.mark.parametrize("name", NAMES)
def test_rule_file_loads_and_is_marked(name: str) -> None:
    doc = load_rule(RULES, name, date(2026, 11, 1))
    assert doc["status"] in {"DEMO", "CONFIRMED"} and doc["effective_from"] == "2024-04-01"


def test_deposit_sum_and_double_with_values() -> None:
    rule = load_rule(RULES, "deposit", date(2026, 11, 1))
    amounts = list(rule["programme_amounts_paise"].values())
    total = sum(amounts)
    assert required_deposit_paise(amounts, False, rule) == total
    assert required_deposit_paise(amounts, True, rule) == total * 2
    assert required_deposit_paise(amounts, True, rule, is_government=True) == 0



def test_release_paths_have_the_four_paths_and_every_item_has_a_source() -> None:
    doc = load_rule(RULES, "release_paths", date(2026, 11, 1))
    assert set(doc["paths"]) == {"term_completion", "closure", "merger", "conversion"}
    for path in doc["paths"].values():
        assert all(i["source"] for i in path["checklist"])
    assert any(
        i["id"] == "no_pending_complaints"
        for i in doc["paths"]["conversion"]["checklist"]
    )
    assert not any(
        i["id"] == "no_pending_complaints"
        for i in doc["paths"]["closure"]["checklist"]
    )


def test_guard_blocks_demo_rules_outside_development() -> None:
    docs = [load_rule(RULES, n, date(2026, 11, 1)) for n in NAMES]
    startup_guard(docs, "development")
    startup_guard(docs, "demo")
    # In production, if any file is DEMO, it raises RuntimeError
    demo_docs = [{**d, "status": "DEMO"} for d in docs]
    with pytest.raises(RuntimeError):
        startup_guard(demo_docs, "production")
    confirmed_docs = [{**d, "status": "CONFIRMED"} for d in docs]
    startup_guard(confirmed_docs, "production")


def test_table_1_4_programmes_in_rule_and_api() -> None:
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    res = client.get("/api/v1/deposits/programmes")
    assert res.status_code == 200
    data = res.json()
    rule = load_rule(RULES, "deposit", date(2026, 11, 1))
    rule_keys = set(rule["programme_amounts_paise"].keys())
    api_keys = {p["name"] for p in data["programmes"]}
    assert api_keys == rule_keys
    expected_table_1_4 = {
        "Engineering and Technology",
        "Planning",
        "Applied Arts and Crafts",
        "Design",
        "Hotel Management and Catering Technology",
        "Computer Applications",
        "Management",
    }
    assert rule_keys == expected_table_1_4
    assert "Pharmacy" not in rule_keys


def test_coverage_government_exempt() -> None:
    rule = load_rule(RULES, "deposit", date(2026, 11, 1))
    from app.domain.rules import calculate_institution_coverage

    amounts = [150000000, 35000000]
    cov = calculate_institution_coverage(
        programme_amounts_paise=amounts,
        leased_private=True,
        rule=rule,
        is_government=True,
        instruments=[{"amount_paise": 5000000, "badge": "confirmed", "lifecycle": "active"}],
    )
    assert cov["required_paise"] == 0
    assert cov["shortfall_paise"] == 0
    assert cov["confirmed_active_paise"] == 5000000


def test_coverage_leased_land_2x() -> None:
    rule = load_rule(RULES, "deposit", date(2026, 11, 1))
    from app.domain.rules import calculate_institution_coverage

    amounts = [100000000]  # 1 Cr base
    cov = calculate_institution_coverage(
        programme_amounts_paise=amounts,
        leased_private=True,
        rule=rule,
        is_government=False,
        instruments=[],
    )
    # Leased land multiplier is 2x => 2 Cr
    assert cov["required_paise"] == 200000000
    assert cov["shortfall_paise"] == 200000000
    assert cov["confirmed_active_paise"] == 0


def test_coverage_several_fdrs() -> None:
    rule = load_rule(RULES, "deposit", date(2026, 11, 1))
    from app.domain.rules import calculate_institution_coverage

    amounts = [100000000]  # 1 Cr base
    # Owned land => 1x => 1 Cr required
    instruments = [
        {"amount_paise": 40000000, "badge": "confirmed", "lifecycle": "active"},
        {"amount_paise": 30000000, "badge": "claimed", "lifecycle": "pending"},
        {"amount_paise": 20000000, "badge": "confirmed", "lifecycle": "released"},  # Not active
        {"amount_paise": 25000000, "badge": "confirmed", "lifecycle": "active"},
    ]
    cov = calculate_institution_coverage(
        programme_amounts_paise=amounts,
        leased_private=False,
        rule=rule,
        is_government=False,
        instruments=instruments,
    )
    assert cov["required_paise"] == 100000000
    # confirmed active: 40000000 + 25000000 = 65000000
    assert cov["confirmed_active_paise"] == 65000000
    # claimed only: 30000000
    assert cov["claimed_only_paise"] == 30000000
    # shortfall: 100000000 - 65000000 = 35000000
    assert cov["shortfall_paise"] == 35000000
