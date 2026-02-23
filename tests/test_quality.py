"""Low-friction tests for data quality checks."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.quality import check_date_ranges, check_duplicates, check_required_columns


def test_required_columns_missing_fails() -> None:
    df = pd.DataFrame({"unternehmen": ["A"]})
    result = check_required_columns(df, ["unternehmen", "status"])
    assert result["status"] == "FAIL"
    assert "status" in result["missing"]


def test_date_ranges_future_date_warns() -> None:
    df = pd.DataFrame({"bewerbungsdatum": ["2099-01-01", "2024-02-01"]})
    result = check_date_ranges(df, "bewerbungsdatum")
    assert result["status"] == "WARN"
    assert int(result.get("future_count", 0)) >= 1


def test_duplicates_warns() -> None:
    df = pd.DataFrame(
        {
            "unternehmen": ["Firma A", "Firma A", "Firma B"],
            "stelle": ["Data Engineer", "Data Engineer", "Analyst"],
            "bewerbungsdatum": ["2024-01-10", "2024-01-10", "2024-01-11"],
        }
    )
    result = check_duplicates(df)
    assert result["status"] == "WARN"
    assert int(result["duplicate_count"]) == 2


if __name__ == "__main__":
    test_required_columns_missing_fails()
    test_date_ranges_future_date_warns()
    test_duplicates_warns()
    print("tests/test_quality.py: ok")
