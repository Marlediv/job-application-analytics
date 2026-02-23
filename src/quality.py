"""Data-quality checks used during ingestion."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd


def _result(name: str, status: str, message: str, **extra: object) -> dict[str, object]:
    payload: dict[str, object] = {"name": name, "status": status, "message": message}
    payload.update(extra)
    return payload


def check_required_columns(df: pd.DataFrame, required: Sequence[str]) -> dict[str, object]:
    missing = [col for col in required if col not in df.columns]
    if missing:
        return _result(
            "required_columns",
            "FAIL",
            f"Pflichtspalten fehlen: {', '.join(missing)}",
            ok=False,
            missing=missing,
        )
    return _result("required_columns", "PASS", "Alle Pflichtspalten vorhanden.", ok=True, missing=[])


def check_date_ranges(df: pd.DataFrame, date_col: str) -> dict[str, object]:
    if date_col not in df.columns:
        return _result("date_ranges", "WARN", f"Spalte '{date_col}' fehlt.", ok=False, warnings=["missing_date_col"])

    date_series = pd.to_datetime(df[date_col], errors="coerce")
    valid_dates = date_series.dropna()
    if valid_dates.empty:
        return _result("date_ranges", "WARN", "Datumswerte sind komplett leer oder ungueltig.", ok=False, warnings=["empty_dates"])

    today = pd.Timestamp.today().normalize()
    future_count = int((valid_dates > today).sum())
    if future_count > 0:
        return _result(
            "date_ranges",
            "WARN",
            f"{future_count} Datumswert(e) liegen in der Zukunft.",
            ok=False,
            warnings=["future_dates"],
            future_count=future_count,
        )
    return _result("date_ranges", "PASS", "Datumsbereich plausibel.", ok=True, warnings=[])


def check_status_values(df: pd.DataFrame, allowed_statuses: Sequence[str]) -> dict[str, object]:
    if "status" not in df.columns:
        return _result("status_values", "WARN", "Spalte 'status' fehlt.", ok=False, unknown_values=[])

    if not allowed_statuses:
        return _result("status_values", "PASS", "Keine Statusliste hinterlegt, Check uebersprungen.", ok=True, unknown_values=[])

    allowed_tokens = [token.strip().lower() for token in allowed_statuses if token and token.strip()]
    status_series = df["status"].fillna("").astype(str).str.strip().str.lower()
    status_series = status_series[status_series != ""]
    if status_series.empty:
        return _result("status_values", "WARN", "Keine befuellten Statuswerte vorhanden.", ok=False, unknown_values=[])

    unknown = status_series[~status_series.apply(lambda v: any(token in v for token in allowed_tokens))]
    if unknown.empty:
        return _result("status_values", "PASS", "Statuswerte innerhalb erwarteter Muster.", ok=True, unknown_values=[])

    samples = sorted(unknown.unique().tolist())[:5]
    return _result(
        "status_values",
        "WARN",
        f"Unbekannte Statuswerte gefunden (Beispiele: {', '.join(samples)}).",
        ok=False,
        unknown_values=samples,
        unknown_count=int(unknown.shape[0]),
    )


def check_duplicates(
    df: pd.DataFrame,
    subset: Sequence[str] = ("unternehmen", "stelle", "bewerbungsdatum"),
) -> dict[str, object]:
    available = [col for col in subset if col in df.columns]
    if not available:
        return _result("duplicates", "WARN", "Keine Duplicate-Check-Spalten vorhanden.", ok=False, duplicate_count=0)

    duplicate_mask = df.duplicated(subset=available, keep=False)
    duplicate_count = int(duplicate_mask.sum())
    if duplicate_count > 0:
        return _result(
            "duplicates",
            "WARN",
            f"{duplicate_count} potenzielle Duplikate erkannt (Subset: {', '.join(available)}).",
            ok=False,
            duplicate_count=duplicate_count,
        )

    return _result(
        "duplicates",
        "PASS",
        f"Keine Duplikate im Subset {', '.join(available)}.",
        ok=True,
        duplicate_count=0,
    )
