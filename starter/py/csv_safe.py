_DANGEROUS = ("=", "+", "-", "@", "\t", "\r")


def csv_safe(value) -> str:
    """Neutralise spreadsheet formulas in exported cells."""
    s = "" if value is None else str(value)
    return "'" + s if s.startswith(_DANGEROUS) else s
