from dataclasses import dataclass


@dataclass(frozen=True)
class Action:
    code: str
    label: str


NONE = Action("none", "Nothing to do")


def next_action(
    *,
    role: str,  # institution | regional | bureau | auditor
    lifecycle: str,  # pending | active | matured | renewed | released
    badge: str,  # claimed | confirmed | stale | changed
    docs_complete: bool,
    open_flags: int,
    confirmation_status: str
    | None,  # requested | confirmed | rejected | unavailable | None
    days_to_maturity: int,
    expiring_days: int,
    has_replacement: bool,
    release_status: str
    | None,  # draft | submitted | verified | approved | rejected | released | None
) -> Action:
    """The ONE source of truth for the primary button. Order of checks is the priority."""
    if role == "institution":
        if lifecycle == "pending" and not docs_complete:
            return Action("upload_documents", "Upload the missing documents")
        if confirmation_status == "requested":
            return Action("return_bank_letter", "Upload the bank's signed reply")
        if (
            lifecycle == "active"
            and 0 <= days_to_maturity <= expiring_days
            and not has_replacement
        ):
            return Action("add_renewal", "Add the renewal FDR")
        if lifecycle == "matured" and not has_replacement and release_status is None:
            return Action("add_renewal", "Add the renewal FDR")
        return NONE
    if role == "regional":
        if release_status == "submitted":
            return Action("verify_release", "Verify the release request")
        if confirmation_status == "unavailable":
            return Action("retry_confirmation", "Retry bank confirmation")
        if confirmation_status == "rejected" or (
            lifecycle == "pending" and open_flags > 0
        ):
            return Action("review_flags", "Review the flagged issues")
        if lifecycle == "pending" and docs_complete and confirmation_status is None:
            return Action("request_confirmation", "Request bank confirmation")
        if lifecycle == "pending" and badge == "confirmed":
            return Action("accept_record", "Accept the record")
        if lifecycle == "active" and badge in ("stale", "changed"):
            return Action("request_confirmation", "Request bank confirmation again")
        if lifecycle == "matured" and not has_replacement and release_status is None:
            return Action("contact_institution", "Contact the institution")
        return NONE
    if role == "bureau":
        if release_status == "verified":
            return Action("approve_release", "Approve the release")
        return NONE
    return NONE  # auditor: read-only


def dashboard_bucket(lifecycle: str, days_to_maturity: int, expiring_days: int) -> str:
    """pending | active | expiring | matured | renewed | released (the statement's six counters)."""
    if lifecycle == "active" and 0 <= days_to_maturity <= expiring_days:
        return "expiring"
    return lifecycle
