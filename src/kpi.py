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

    return pd.read_csv(csv_path)


def _require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [col for col in columns if col not in df.columns]
    if missing:
        raise ValueError(
            "Fehlende Spalte(n) fuer KPI-Berechnung: "
            f"{', '.join(missing)}"
        )


def _normalized_status(df: pd.DataFrame) -> pd.Series:
    _require_columns(df, ["status"])

    status = df["status"].fillna("").astype(str).str.strip().str.lower()
    status = (
        status.str.replace("ä", "ae", regex=False)
        .str.replace("ö", "oe", regex=False)
        .str.replace("ü", "ue", regex=False)
        .str.replace("ß", "ss", regex=False)
    )
    return status


def _interview_mask(df: pd.DataFrame) -> pd.Series:
    status = _normalized_status(df)
    return status.str.contains(r"interview|gespraech", regex=True)


def _rejection_mask(df: pd.DataFrame) -> pd.Series:
    status = _normalized_status(df)
    return status.str.contains(r"absage|abgelehnt", regex=True)


def _offer_mask(df: pd.DataFrame) -> pd.Series:
    status = _normalized_status(df)
    return status.str.contains(r"angebot|offer|zusage", regex=True)


def total_applications(df: pd.DataFrame) -> int:
    return int(len(df))


def active_applications(df: pd.DataFrame) -> int:
    status = _normalized_status(df)
    inactive = status.str.contains(r"absage|abgelehnt|angebot|offer|zusage", regex=True)
    return int((~inactive).sum())


def rejection_count(df: pd.DataFrame) -> int:
    return int(_rejection_mask(df).sum())


def interview_count(df: pd.DataFrame) -> int:
    return int(_interview_mask(df).sum())


def rejection_rate(df: pd.DataFrame) -> float:
    total = total_applications(df)
    return float(rejection_count(df) / total) if total else 0.0


def interview_rate(df: pd.DataFrame) -> float:
    total = total_applications(df)
    return float(interview_count(df) / total) if total else 0.0


def avg_wait_time(df: pd.DataFrame) -> float:
    _require_columns(df, ["wartezeit_tage"])
    series = pd.to_numeric(df["wartezeit_tage"], errors="coerce")
    return float(series.mean()) if not series.dropna().empty else float("nan")


def kpi_by_source(df: pd.DataFrame) -> pd.DataFrame:
    _require_columns(df, ["quelle", "status"])
    out = df.copy()
    out["quelle"] = out["quelle"].fillna("Unbekannt").astype(str).str.strip()
    out["interviewed"] = _interview_mask(out)

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


def kpi_by_work_model(df: pd.DataFrame) -> pd.DataFrame:
    _require_columns(df, ["arbeitsmodell", "status"])
    out = df.copy()
    out["arbeitsmodell"] = out["arbeitsmodell"].fillna("Unbekannt").astype(str).str.strip()
    out["interviewed"] = _interview_mask(out)

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
    out = df.copy()
    out["ranking_score"] = pd.to_numeric(out["ranking_score"], errors="coerce")
    out["interviewed"] = _interview_mask(out)
    return out[["ranking_score", "interviewed"]].dropna(subset=["ranking_score"])
