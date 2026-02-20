"""Lightweight tests for status flag normalization and ghosting KPIs."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.kpi import _ensure_status_flags


def test_ensure_status_flags_sets_expected_booleans() -> None:
    df = pd.DataFrame(
        {
            "status": [
                "Absage erhalten",
                "INTERVIEW Runde 1",
                "Eingangsbestätigung erhalten",
                "Angebot vorliegend",
                "In Prüfung",
            ],
            "wartezeit_tage": [12, 35, 5, 10, 45],
        }
    )

    out = _ensure_status_flags(df)

    assert bool(out.loc[0, "is_rejection"]) is True
    assert bool(out.loc[0, "is_active"]) is False
    assert bool(out.loc[1, "is_interview"]) is True
    assert bool(out.loc[1, "is_response"]) is True
    assert bool(out.loc[1, "is_ghosted"]) is True
    assert bool(out.loc[2, "is_response"]) is True
    assert bool(out.loc[3, "is_offer"]) is True
    assert bool(out.loc[3, "is_active"]) is False
    assert bool(out.loc[4, "is_active"]) is True
    assert bool(out.loc[4, "is_ghosted"]) is True


def test_ensure_status_flags_handles_missing_wait_time() -> None:
    df = pd.DataFrame({"status": ["In Pruefung", "Antwort eingegangen"]})
    out = _ensure_status_flags(df)
    assert out["is_ghosted"].sum() == 0


if __name__ == "__main__":
    test_ensure_status_flags_sets_expected_booleans()
    test_ensure_status_flags_handles_missing_wait_time()
    print("tests/test_kpi_flags.py: ok")
