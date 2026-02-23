"""KPI calculations for job application analytics."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def load_processed(path: str | Path = "data/processed/applications.csv") -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.is_absolute():
        repo_root = Path(__file__).resolve().parents[1]
        csv_path = repo_root / csv_path

    if not csv_path.exists():
        raise FileNotFoundError(f"Processed CSV nicht gefunden: {csv_path}")

    df = pd.read_csv(csv_path)
    return _ensure_status_flags(df)


def _require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [col for col in columns if col not in df.columns]
    if missing:
        raise ValueError(
            "Fehlende Spalte(n) fuer KPI-Berechnung: "
            f"{', '.join(missing)}"
        )


def _normalized_status(df: pd.DataFrame) -> pd.Series:
    out = _ensure_status_flags(df)
    return out["status_clean"]


def _ensure_status_flags(df: pd.DataFrame) -> pd.DataFrame:
    _require_columns(df, ["status"])

    out = df.copy()
    out["status_clean"] = out["status"].fillna("").astype(str).str.strip().str.lower()
    status_for_match = (
        out["status_clean"]
        .str.replace("ä", "ae", regex=False)
        .str.replace("ö", "oe", regex=False)
        .str.replace("ü", "ue", regex=False)
        .str.replace("ß", "ss", regex=False)
    )

    out["is_rejection"] = status_for_match.str.contains(r"absage|abgelehnt", regex=True)
    out["is_offer"] = status_for_match.str.contains(r"angebot|offer|zusage", regex=True)
    out["is_interview"] = status_for_match.str.contains(r"interview|gespraech|gesprach|gespräch", regex=True)

    response_text = status_for_match.str.contains(
        r"eingangsbestaetigung|eingangsbestatigung|eingangsbestaetigung|eingangsbestätigung|rueckmeldung|ruckmeldung|rückmeldung|antwort",
        regex=True,
    )
    out["is_response"] = response_text | out["is_rejection"] | out["is_offer"] | out["is_interview"]
    out["is_active"] = ~out["is_rejection"] & ~out["is_offer"]

    if "wartezeit_tage" in out.columns:
        wait_days = pd.to_numeric(out["wartezeit_tage"], errors="coerce")
        out["is_ghosted"] = out["is_active"] & (wait_days >= 30)
    else:
        out["is_ghosted"] = False

    return out


def _interview_mask(df: pd.DataFrame) -> pd.Series:
    out = _ensure_status_flags(df)
    return out["is_interview"]


def _rejection_mask(df: pd.DataFrame) -> pd.Series:
    out = _ensure_status_flags(df)
    return out["is_rejection"]


def _offer_mask(df: pd.DataFrame) -> pd.Series:
    out = _ensure_status_flags(df)
    return out["is_offer"]


def total_applications(df: pd.DataFrame) -> int:
    return int(len(df))


def active_applications(df: pd.DataFrame) -> int:
    out = _ensure_status_flags(df)
    return int(out["is_active"].sum())


def rejection_count(df: pd.DataFrame) -> int:
    return int(_rejection_mask(df).sum())


def interview_count(df: pd.DataFrame) -> int:
    return int(_interview_mask(df).sum())


def offer_count(df: pd.DataFrame) -> int:
    return int(_offer_mask(df).sum())


def rejection_rate(df: pd.DataFrame) -> float:
    total = total_applications(df)
    return float(rejection_count(df) / total) if total else 0.0


def interview_rate(df: pd.DataFrame) -> float:
    total = total_applications(df)
    return float(interview_count(df) / total) if total else 0.0


def response_count(df: pd.DataFrame) -> int:
    out = _ensure_status_flags(df)
    return int(out["is_response"].sum())


def response_rate(df: pd.DataFrame) -> float:
    total = total_applications(df)
    return float(response_count(df) / total) if total else 0.0


def ghosted_count(df: pd.DataFrame) -> int:
    out = _ensure_status_flags(df)
    return int(out["is_ghosted"].sum())


def ghosted_rate(df: pd.DataFrame) -> float:
    total = total_applications(df)
    return float(ghosted_count(df) / total) if total else 0.0


def avg_wait_time(df: pd.DataFrame) -> float:
    _require_columns(df, ["wartezeit_tage"])
    series = pd.to_numeric(df["wartezeit_tage"], errors="coerce")
    return float(series.mean()) if not series.dropna().empty else float("nan")


def kpi_by_source(df: pd.DataFrame) -> pd.DataFrame:
    _require_columns(df, ["quelle", "status"])
    out = _ensure_status_flags(df)
    out["quelle"] = out["quelle"].fillna("Unbekannt").astype(str).str.strip()
    out["interviewed"] = out["is_interview"]

    grouped = (
        out.groupby("quelle", dropna=False)
        .agg(counts=("status", "size"), interviewed=("interviewed", "sum"))
        .reset_index()
    )
    grouped["interview_rate"] = np.where(
        grouped["counts"] > 0,
        grouped["interviewed"] / grouped["counts"],
        0.0,
    )
    return grouped.sort_values("counts", ascending=False)


def rate_by_source(df: pd.DataFrame, flag_col: str, source_col: str = "quelle") -> pd.DataFrame:
    _require_columns(df, [source_col, flag_col])

    out = df.copy()
    out[source_col] = out[source_col].where(out[source_col].notna(), pd.NA)
    out[source_col] = out[source_col].astype("string").str.strip()
    out = out[out[source_col].notna() & out[source_col].ne("")]

    if out.empty:
        return pd.DataFrame(columns=["quelle", "counts", "flagged", "rate"])

    all_sources = pd.Index(out[source_col].dropna().unique(), name="quelle")
    out["_flag"] = pd.to_numeric(out[flag_col], errors="coerce").fillna(0)

    grouped = (
        out.groupby(source_col, dropna=False)
        .agg(counts=(source_col, "size"), flagged=("_flag", "sum"))
        .reindex(all_sources)
    )
    grouped["counts"] = grouped["counts"].fillna(0)
    grouped["flagged"] = grouped["flagged"].fillna(0)
    grouped["rate"] = np.where(grouped["counts"] > 0, grouped["flagged"] / grouped["counts"], 0.0)
    grouped["rate"] = grouped["rate"].fillna(0.0)

    result = grouped.reset_index()
    return result.sort_values(["counts", "quelle"], ascending=[False, True]).reset_index(drop=True)


def kpi_by_work_model(df: pd.DataFrame) -> pd.DataFrame:
    _require_columns(df, ["arbeitsmodell", "status"])
    out = _ensure_status_flags(df)
    out["arbeitsmodell"] = out["arbeitsmodell"].fillna("Unbekannt").astype(str).str.strip()
    out["interviewed"] = out["is_interview"]

    grouped = (
        out.groupby("arbeitsmodell", dropna=False)
        .agg(counts=("status", "size"), interviewed=("interviewed", "sum"))
        .reset_index()
    )
    grouped["interview_rate"] = np.where(
        grouped["counts"] > 0,
        grouped["interviewed"] / grouped["counts"],
        0.0,
    )
    return grouped.sort_values("counts", ascending=False)


def wait_time_by_status(df: pd.DataFrame) -> pd.DataFrame:
    _require_columns(df, ["status", "wartezeit_tage"])
    out = df.copy()
    out["status"] = out["status"].fillna("Unbekannt").astype(str).str.strip()
    out["wartezeit_tage"] = pd.to_numeric(out["wartezeit_tage"], errors="coerce")

    grouped = (
        out.groupby("status", dropna=False)["wartezeit_tage"]
        .agg(avg_wait="mean", median_wait="median", counts="size")
        .reset_index()
        .sort_values("counts", ascending=False)
    )
    return grouped


def ranking_vs_interview(df: pd.DataFrame) -> pd.DataFrame:
    _require_columns(df, ["ranking_score", "status"])
    out = _ensure_status_flags(df)
    out["ranking_score"] = pd.to_numeric(out["ranking_score"], errors="coerce")
    out["interviewed"] = out["is_interview"]
    return out[["ranking_score", "interviewed"]].dropna(subset=["ranking_score"])


def funnel_table(df: pd.DataFrame) -> pd.DataFrame:
    out = _ensure_status_flags(df)
    total = total_applications(out)
    response = int(out["is_response"].sum())
    interview = int(out["is_interview"].sum())
    offer = int(out["is_offer"].sum())

    stages = [
        ("Bewerbungen", total),
        ("Rueckmeldung", response),
        ("Interview", interview),
        ("Angebot", offer),
    ]

    rows: list[dict[str, float | int | str]] = []
    prev_count: int | None = None
    for stage_name, count in stages:
        rate_from_prev = float(count / prev_count) if prev_count and prev_count > 0 else float("nan")
        rate_from_total = float(count / total) if total > 0 else 0.0
        rows.append(
            {
                "stage": stage_name,
                "count": int(count),
                "rate_from_prev": rate_from_prev,
                "rate_from_total": rate_from_total,
            }
        )
        prev_count = int(count)

    return pd.DataFrame(rows, columns=["stage", "count", "rate_from_prev", "rate_from_total"])
