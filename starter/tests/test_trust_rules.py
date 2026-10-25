import json
from datetime import date, datetime, timedelta, timezone
import pytest
from trust import Confirmation, badge
from rules import load_rule, required_deposit_paise

NOW = datetime(2026, 11, 1, tzinfo=timezone.utc)
INST = dict(ref_no="1234", bank_code="SBIN", amount_paise=10_000_000, maturity_date="2027-03-14")
def conf(**kw):
    d = dict(fields=dict(INST), method="signed_letter", confirmed_at=NOW - timedelta(days=5),
             expires_at=NOW + timedelta(days=60))
    d.update(kw); return Confirmation(**d)

def test_claimed_when_none(): assert badge(INST, [], NOW) == "claimed"
def test_confirmed(): assert badge(INST, [conf()], NOW) == "confirmed"
def test_stale(): assert badge(INST, [conf(expires_at=NOW - timedelta(days=1))], NOW) == "stale"
def test_changed_after_confirm():
    assert badge({**INST, "amount_paise": 9_000_000}, [conf()], NOW) == "changed"
def test_revoked_is_claimed(): assert badge(INST, [conf(revoked=True)], NOW) == "claimed"
def test_latest_confirmation_wins():
    old = conf(confirmed_at=NOW - timedelta(days=90), fields={**INST, "amount_paise": 1})
    assert badge(INST, [old, conf()], NOW) == "confirmed"

def test_rules_effective_dating(tmp_path):
    (tmp_path / "deposit.2024-04-01.json").write_text(json.dumps({"effective_from": "2024-04-01", "leased_private_multiplier": 2}))
    (tmp_path / "deposit.2027-04-01.json").write_text(json.dumps({"effective_from": "2027-04-01", "leased_private_multiplier": 3}))
    assert load_rule(tmp_path, "deposit", date(2026, 11, 1))["leased_private_multiplier"] == 2
    assert load_rule(tmp_path, "deposit", date(2027, 5, 1))["leased_private_multiplier"] == 3
    with pytest.raises(LookupError): load_rule(tmp_path, "deposit", date(2020, 1, 1))

def test_required_deposit_sum_and_double():
    rule = {"leased_private_multiplier": 2}
    assert required_deposit_paise([100, 250], False, rule) == 350
    assert required_deposit_paise([100, 250], True, rule) == 700

