"""Tests for rate_by_source helper."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.kpi import rate_by_source


def test_rate_by_source_zero_flags_returns_zero_rate_per_source() -> None:
    df = pd.DataFrame(
        {
            "quelle": ["LinkedIn", "XING", "LinkedIn"],
            "interviewed_flag": [0, 0, 0],
        }
    )

    out = rate_by_source(df, "interviewed_flag")

    assert out["quelle"].tolist() == ["LinkedIn", "XING"]
    assert out["counts"].tolist() == [2, 1]
    assert out["flagged"].tolist() == [0, 0]
    assert out["rate"].tolist() == [0.0, 0.0]


def test_rate_by_source_mixed_flags() -> None:
    df = pd.DataFrame(
        {
            "quelle": ["LinkedIn", "LinkedIn", "XING"],
            "ghosted_flag": [1, 0, 0],
        }
    )

    out = rate_by_source(df, "ghosted_flag")
    indexed = out.set_index("quelle")

    assert indexed.loc["LinkedIn", "counts"] == 2
    assert indexed.loc["LinkedIn", "flagged"] == 1
    assert indexed.loc["LinkedIn", "rate"] == 0.5
    assert indexed.loc["XING", "counts"] == 1
    assert indexed.loc["XING", "flagged"] == 0
    assert indexed.loc["XING", "rate"] == 0.0


def test_rate_by_source_ignores_nan_and_empty_source() -> None:
    df = pd.DataFrame(
        {
            "quelle": ["LinkedIn", None, "", "  ", "XING"],
            "interviewed_flag": [1, 1, 1, 0, 0],
        }
    )

    out = rate_by_source(df, "interviewed_flag")

    assert set(out["quelle"].tolist()) == {"LinkedIn", "XING"}
    indexed = out.set_index("quelle")
    assert indexed.loc["LinkedIn", "counts"] == 1
    assert indexed.loc["XING", "counts"] == 1


if __name__ == "__main__":
    test_rate_by_source_zero_flags_returns_zero_rate_per_source()
    test_rate_by_source_mixed_flags()
    test_rate_by_source_ignores_nan_and_empty_source()
    print("tests/test_rate_by_source.py: ok")
