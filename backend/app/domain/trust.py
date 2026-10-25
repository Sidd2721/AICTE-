from dataclasses import dataclass
from datetime import datetime
from typing import Any

CONFIRMED_FIELDS = ("ref_no", "bank_code", "amount_paise", "maturity_date")


@dataclass(frozen=True)
class Confirmation:
    fields: dict[str, Any]  # snapshot the bank confirmed
    method: str  # "signed_letter" | "callback" | "manual"
    confirmed_at: datetime
    expires_at: datetime
    revoked: bool = False


def badge(
    instrument: dict[str, Any], confirmations: list[Confirmation], now: datetime
) -> str:
    """claimed | confirmed | stale | changed. Never 'mismatch' from absence of data."""
    live = [c for c in confirmations if not c.revoked]
    if not live:
        return "claimed"
    latest = max(live, key=lambda c: c.confirmed_at)
    for k in CONFIRMED_FIELDS:
        inst_v = instrument.get(k)
        conf_v = latest.fields.get(k)
        if k == "maturity_date":
            if str(inst_v) != str(conf_v):
                return "changed"
        elif inst_v != conf_v:
            return "changed"
    if now >= latest.expires_at:
        return "stale"
    return "confirmed"
