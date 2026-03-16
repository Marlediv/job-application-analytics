"""KPI calculations for job application analytics."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

STATUS_MAP: dict[str, str] = {
    "absage": "Absage",
    "abgelehnt": "Absage",
    "interview": "Interview 1",
    "interview 1": "Interview 1",
    "eingangsbestätigung": "Eingangsbestätigung",
    "eingangsbestaetigung": "Eingangsbestätigung",
    "bewerbung gesendet": "Bewerbung gesendet",
    "keine rückmeldung": "Keine Rückmeldung",
    "keine rueckmeldung": "Keine Rückmeldung",
    "angebot": "Angebot",
    "offer": "Angebot",
    "zusage": "Angebot",
}

STATUS_ORDER: list[str] = [
    "Bewerbung gesendet",
    "Eingangsbestätigung",
    "Interview 1",
    "Angebot",
    "Absage",
    "Keine Rückmeldung",
]

_RESPONSE_STATUSES: set[str] = {"Eingangsbestätigung", "Interview 1", "Absage", "Angebot"}
_OPEN_WAIT_STATUSES: set[str] = {
    "Bewerbung gesendet",
    "Eingangsbestätigung",
    "Keine Rückmeldung",
    "Interview 1",
}


def _fold_umlauts(series: pd.Series) -> pd.Series:
    return (
        series.str.replace("ä", "ae", regex=False)
        .str.replace("ö", "oe", regex=False)
        .str.replace("ü", "ue", regex=False)
        .str.replace("ß", "ss", regex=False)
    )


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
            "Fehlende Spalte(n) für KPI-Berechnung: "
            f"{', '.join(missing)}"
        )


def _normalized_status(df: pd.DataFrame) -> pd.Series:
    out = _ensure_status_flags(df)
    return out["status_clean"]


def _coerce_datetime_column(series: pd.Series) -> pd.Series:
    values = pd.to_datetime(series, errors="coerce")
    if getattr(values.dt, "tz", None) is not None:
        values = values.dt.tz_localize(None)
    return values


def _reference_today(today: datetime | pd.Timestamp | None = None) -> pd.Timestamp:
    if today is None:
        return pd.Timestamp(datetime.now().date())

    timestamp = pd.Timestamp(today)
    if timestamp.tzinfo is not None:
        timestamp = timestamp.tz_localize(None)
    return timestamp.normalize()


def _effective_wait_time(out: pd.DataFrame, today: datetime | pd.Timestamp | None = None) -> pd.Series:
    if "wartezeit_tage" in out.columns:
        base_wait = pd.to_numeric(out["wartezeit_tage"], errors="coerce")
    else:
        base_wait = pd.Series(np.nan, index=out.index, dtype="float64")
    effective = base_wait.copy()

    reference_today = _reference_today(today)
    last_contact = _coerce_datetime_column(out["letzter_kontakt"]) if "letzter_kontakt" in out.columns else pd.Series(pd.NaT, index=out.index)
    application_date = (
        _coerce_datetime_column(out["bewerbungsdatum"])
        if "bewerbungsdatum" in out.columns
        else pd.Series(pd.NaT, index=out.index)
    )
    open_status_mask = out["status_canonical"].isin(_OPEN_WAIT_STATUSES)
    missing_wait_mask = effective.isna() & open_status_mask

    from_last_contact = (reference_today - last_contact).dt.days
    from_application_date = (reference_today - application_date).dt.days
    fallback_wait = from_last_contact.where(last_contact.notna(), from_application_date)

    effective = effective.where(~missing_wait_mask, fallback_wait)
    effective = effective.clip(lower=0)
    return pd.to_numeric(effective, errors="coerce")


def _ensure_status_flags(df: pd.DataFrame, today: datetime | pd.Timestamp | None = None) -> pd.DataFrame:
    _require_columns(df, ["status"])

    out = df.copy()
    raw_status = out["status"].fillna("").astype(str).str.strip()
    out["status_clean"] = raw_status.str.lower()
    status_folded = _fold_umlauts(out["status_clean"])

    mapped = out["status_clean"].map(STATUS_MAP)
    mapped_folded = status_folded.map(STATUS_MAP)
    canonical = mapped.combine_first(mapped_folded)
    canonical = canonical.mask(canonical.isna() & status_folded.str.contains(r"absage|abgelehnt", regex=True), "Absage")
    canonical = canonical.mask(canonical.isna() & status_folded.str.contains(r"angebot|offer|zusage", regex=True), "Angebot")
    canonical = canonical.mask(
        canonical.isna() & status_folded.str.contains(r"interview|gespraech|gesprach", regex=True), "Interview 1"
    )
    canonical = canonical.mask(
        canonical.isna() & status_folded.str.contains(r"eingangsbestaetigung|eingangsbestatigung", regex=True),
        "Eingangsbestätigung",
    )
    canonical = canonical.mask(
        canonical.isna() & status_folded.str.contains(r"keine rueckmeldung|keine ruckmeldung|keine rückmeldung", regex=True),
        "Keine Rückmeldung",
    )
    out["status_canonical"] = canonical.fillna(raw_status.where(raw_status.ne(""), "Unbekannt"))

    out["is_rejection"] = out["status_canonical"].eq("Absage")
    out["is_offer"] = out["status_canonical"].eq("Angebot")
    out["is_interview"] = out["status_canonical"].str.startswith("Interview", na=False)
    out["is_response"] = out["status_canonical"].isin(_RESPONSE_STATUSES)
    out["is_active"] = ~out["is_rejection"] & ~out["is_offer"]

    out["effective_wait_time"] = _effective_wait_time(out, today=today)
    ghosted_status_excluded = ["Absage", "Angebot"]
    out["is_ghosted"] = (
        out["status_canonical"].eq("Keine Rückmeldung")
        | (
            ~out["status_canonical"].isin(ghosted_status_excluded)
            & (out["effective_wait_time"] >= 21)
        )
    ).astype(bool)

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
    out = _ensure_status_flags(df)
    series = pd.to_numeric(out["effective_wait_time"], errors="coerce")
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
    _require_columns(df, ["status"])
    out = _ensure_status_flags(df)
    out["effective_wait_time"] = pd.to_numeric(out["effective_wait_time"], errors="coerce")

    grouped = (
        out.groupby("status_canonical", dropna=False)["effective_wait_time"]
        .agg(avg_wait="mean", median_wait="median", counts="size", valid_wait_count="count")
        .reset_index()
        .sort_values("counts", ascending=False)
    )
    grouped = grouped.rename(columns={"status_canonical": "status"})
    return grouped


def longest_no_response_case(df: pd.DataFrame) -> pd.Series | None:
    _require_columns(df, ["status"])
    out = _ensure_status_flags(df)
    if "unternehmen" not in out.columns:
        return None

    candidates = out.copy()
    candidates["unternehmen"] = candidates["unternehmen"].astype("string").str.strip()
    candidates["effective_wait_time"] = pd.to_numeric(candidates["effective_wait_time"], errors="coerce")
    candidates = candidates.loc[
        candidates["unternehmen"].notna()
        & candidates["unternehmen"].ne("")
        & candidates["effective_wait_time"].notna()
        & (candidates["effective_wait_time"] > 0)
    ]
    if candidates.empty:
        return None

    no_response = candidates.loc[candidates["status_canonical"].eq("Keine Rückmeldung")]
    if not no_response.empty:
        return no_response.sort_values("effective_wait_time", ascending=False).iloc[0]

    ghosted = candidates.loc[candidates["is_ghosted"]]
    if not ghosted.empty:
        return ghosted.sort_values("effective_wait_time", ascending=False).iloc[0]

    return None


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
        ("Rückmeldung", response),
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
