from app.domain.csv_safe import csv_safe


def test_formula_prefixes_are_neutralised():
    for bad in ("=1+1", "+cmd", "-2", "@SUM(A1)", "\tx", "\rx"):
        assert csv_safe(bad).startswith("'")
def test_normal_text_unchanged(): assert csv_safe("State Bank") == "State Bank"
def test_none_is_empty(): assert csv_safe(None) == ""
def test_numbers_are_text(): assert csv_safe(100) == "100"
