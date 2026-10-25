from dataclasses import dataclass
from datetime import datetime

CONFIRMED_FIELDS = ("ref_no", "bank_code", "amount_paise", "maturity_date")

@dataclass(frozen=True)
class Confirmation:
    fields: dict          # snapshot the bank confirmed
    method: str           # "signed_letter" | "callback" | "manual"
    confirmed_at: datetime
    expires_at: datetime
    revoked: bool = False

def badge(instrument: dict, confirmations: list[Confirmation], now: datetime) -> str:
    """claimed | confirmed | stale | changed. Never 'mismatch' from absence of data."""
    live = [c for c in confirmations if not c.revoked]
    if not live:
        return "claimed"
    latest = max(live, key=lambda c: c.confirmed_at)
    if any(instrument.get(k) != latest.fields.get(k) for k in CONFIRMED_FIELDS):
        return "changed"          # edited after the bank confirmed
    if now >= latest.expires_at:
        return "stale"
    return "confirmed"
