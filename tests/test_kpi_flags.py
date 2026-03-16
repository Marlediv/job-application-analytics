"""Lightweight tests for status flag normalization and ghosting KPIs."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.insights import build_key_insights
from src.kpi import _ensure_status_flags, longest_no_response_case


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


def test_status_normalization_maps_canonical_values() -> None:
    df = pd.DataFrame(
        {
            "status": [
                " interview ",
                "eingangsbestaetigung",
                "  Offer  ",
                "Spezialstatus intern",
            ]
        }
    )

    out = _ensure_status_flags(df)

    assert out["status_clean"].tolist() == ["interview", "eingangsbestaetigung", "offer", "spezialstatus intern"]
    assert out["status_canonical"].tolist() == [
        "Interview 1",
        "Eingangsbestätigung",
        "Angebot",
        "Spezialstatus intern",
    ]


def test_effective_wait_time_uses_fallback_dates_for_open_statuses() -> None:
    reference_today = datetime(2026, 3, 16)
    df = pd.DataFrame(
        {
            "status": [
                "Absage",
                "Eingangsbestätigung",
                "Bewerbung gesendet",
            ],
            "wartezeit_tage": [11, None, None],
            "letzter_kontakt": [None, "2026-03-10", None],
            "bewerbungsdatum": ["2026-03-01", "2026-03-01", "2026-03-12"],
        }
    )

    out = _ensure_status_flags(df, today=reference_today)

    assert out["effective_wait_time"].tolist() == [11.0, 6.0, 4.0]


def test_ghosting_marks_no_response_status_even_without_wait_time() -> None:
    df = pd.DataFrame(
        {
            "status": ["Keine Rückmeldung"],
            "wartezeit_tage": [0],
        }
    )

    out = _ensure_status_flags(df)

    assert bool(out.loc[0, "is_ghosted"]) is True


def test_ghosting_marks_open_status_when_effective_wait_reaches_threshold() -> None:
    df = pd.DataFrame(
        {
            "status": ["Eingangsbestätigung"],
            "wartezeit_tage": [30],
        }
    )

    out = _ensure_status_flags(df)

    assert bool(out.loc[0, "is_ghosted"]) is True


def test_longest_no_response_case_prioritizes_no_response_status() -> None:
    df = pd.DataFrame(
        {
            "unternehmen": ["Informationsfabrik", "LikeMind Recruitment"],
            "status": ["Keine Rückmeldung", "Eingangsbestätigung"],
            "wartezeit_tage": [41, 24],
        }
    )

    case = longest_no_response_case(df)
    insights = build_key_insights(df)

    assert case is not None
    assert str(case["unternehmen"]) == "Informationsfabrik"
    assert any("Längste Wartezeit ohne Antwort: Informationsfabrik (41 Tage, Keine Rückmeldung)." == line for line in insights)


def test_longest_no_response_case_falls_back_to_ghosted_case() -> None:
    df = pd.DataFrame(
        {
            "unternehmen": ["LikeMind Recruitment", "Anderes Unternehmen"],
            "status": ["Eingangsbestätigung", "Absage"],
            "wartezeit_tage": [24, 40],
        }
    )

    case = longest_no_response_case(df)
    insights = build_key_insights(df)

    assert case is not None
    assert str(case["unternehmen"]) == "LikeMind Recruitment"
    assert any("Längste Wartezeit ohne Antwort: LikeMind Recruitment (24 Tage, Eingangsbestätigung)." == line for line in insights)


if __name__ == "__main__":
    test_ensure_status_flags_sets_expected_booleans()
    test_ensure_status_flags_handles_missing_wait_time()
    test_status_normalization_maps_canonical_values()
    test_effective_wait_time_uses_fallback_dates_for_open_statuses()
    test_ghosting_marks_no_response_status_even_without_wait_time()
    test_ghosting_marks_open_status_when_effective_wait_reaches_threshold()
    test_longest_no_response_case_prioritizes_no_response_status()
    test_longest_no_response_case_falls_back_to_ghosted_case()
    print("tests/test_kpi_flags.py: ok")
