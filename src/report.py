"""Generate a reproducible Markdown insight report."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from .kpi import (
    active_applications,
    avg_wait_time,
    ghosted_count,
    ghosted_rate,
    interview_count,
    interview_rate,
    load_processed,
    rejection_count,
    rejection_rate,
    response_count,
    response_rate,
    total_applications,
    wait_time_by_status,
)


REPORT_PATH = Path("reports/insights.md")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _source_performance(df: pd.DataFrame) -> tuple[str | None, str | None]:
    if "quelle" not in df.columns:
        return None, None

    source_df = df.copy()
    source_df["quelle"] = source_df["quelle"].fillna("Unbekannt").astype(str).str.strip()

    grouped = (
        source_df.groupby("quelle", dropna=False)
        .agg(
            applications=("quelle", "size"),
            responses=("is_response", "sum"),
            interviews=("is_interview", "sum"),
        )
        .reset_index()
    )

    if grouped.empty:
        return None, None

    grouped["response_rate"] = grouped["responses"] / grouped["applications"]
    grouped["interview_rate"] = grouped["interviews"] / grouped["applications"]

    top_response_row = grouped.sort_values(["response_rate", "applications"], ascending=[False, False]).iloc[0]
    top_interview_row = grouped.sort_values(["interview_rate", "applications"], ascending=[False, False]).iloc[0]

    response_insight = (
        f"Top-Quelle nach Rueckmeldequote: `{top_response_row['quelle']}` "
        f"({top_response_row['response_rate']:.1%}, n={int(top_response_row['applications'])})."
    )
    interview_insight = (
        f"Top-Quelle nach Interviewquote: `{top_interview_row['quelle']}` "
        f"({top_interview_row['interview_rate']:.1%}, n={int(top_interview_row['applications'])})."
    )
    return response_insight, interview_insight


def _highest_wait_status(df: pd.DataFrame) -> str | None:
    if "wartezeit_tage" not in df.columns or "status" not in df.columns:
        return None

    status_wait = wait_time_by_status(df)
    if status_wait.empty:
        return None

    top_wait = status_wait.sort_values("median_wait", ascending=False).iloc[0]
    return (
        f"Status mit hoechster medianer Wartezeit: `{top_wait['status']}` "
        f"({float(top_wait['median_wait']):.1f} Tage, n={int(top_wait['counts'])})."
    )


def _build_insights(df: pd.DataFrame) -> list[str]:
    insights: list[str] = []

    top_response, top_interview = _source_performance(df)
    if top_response:
        insights.append(top_response)
    else:
        insights.append("Keine Quelle verfuegbar: Vergleich nach Rueckmeldequote nicht moeglich.")

    if top_interview:
        insights.append(top_interview)
    else:
        insights.append("Keine Quelle verfuegbar: Vergleich nach Interviewquote nicht moeglich.")

    wait_status = _highest_wait_status(df)
    if wait_status:
        insights.append(wait_status)
    else:
        insights.append("Keine robuste Wartezeit-Auswertung nach Status moeglich.")

    ghosted = ghosted_count(df)
    ghosted_pct = ghosted_rate(df)
    insights.append(
        f"Ghosting: {ghosted} Bewerbungen ({ghosted_pct:.1%}) gelten als ghosted. "
        "Empfehlung: spaetestens nach 14 Tagen aktiv nachfassen."
    )

    interviews = interview_count(df)
    if interviews == 0:
        insights.append("Noch keine Interviews im Datensatz.")
    else:
        insights.append(f"Interviews im Datensatz: {interviews} ({interview_rate(df):.1%} der Bewerbungen).")

    return insights


def _format_markdown(df: pd.DataFrame) -> str:
    timestamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")

    total = total_applications(df)
    active = active_applications(df)
    responses = response_count(df)
    responses_rate = response_rate(df)
    interviews = interview_count(df)
    interviews_rate = interview_rate(df)
    rejections = rejection_count(df)
    rejections_rate = rejection_rate(df)
    ghosted = ghosted_count(df)
    ghosted_pct = ghosted_rate(df)
    avg_wait = avg_wait_time(df) if "wartezeit_tage" in df.columns else float("nan")

    kpi_rows = [
        ("Gesamtbewerbungen", str(total)),
        ("Aktive Bewerbungen", str(active)),
        ("Rueckmeldungen", str(responses)),
        ("Rueckmeldequote", f"{responses_rate:.1%}"),
        ("Interviews", str(interviews)),
        ("Interviewquote", f"{interviews_rate:.1%}"),
        ("Absagen", str(rejections)),
        ("Absagequote", f"{rejections_rate:.1%}"),
        ("Ghosted", str(ghosted)),
        ("Ghosting-Quote", f"{ghosted_pct:.1%}"),
        ("Durchschnittliche Wartezeit", "-" if pd.isna(avg_wait) else f"{avg_wait:.1f} Tage"),
    ]

    insight_lines = "\n".join(f"- {insight}" for insight in _build_insights(df))
    kpi_table = "\n".join(f"| {name} | {value} |" for name, value in kpi_rows)

    return (
        "# Key Insights Report\n\n"
        f"Erstellt am: {timestamp}\n\n"
        "## KPI Summary\n\n"
        "| KPI | Wert |\n"
        "| --- | --- |\n"
        f"{kpi_table}\n\n"
        "## Key Insights\n\n"
        f"{insight_lines}\n\n"
        "## Methodik\n\n"
        "- Status-Flags werden zentral in `src.kpi._ensure_status_flags` normiert (case-insensitive Matching).\n"
        "- `is_response` erfasst Rueckmeldung/Antwort sowie Absage, Angebot und Interview als Reaktionsereignisse.\n"
        "- Ghosting ist definiert als `is_active == True` und `wartezeit_tage >= 30`.\n"
        "- Wenn `wartezeit_tage` fehlt, wird Ghosting als 0 behandelt.\n"
    )


def generate_report(output_path: str | Path = REPORT_PATH) -> Path:
    df = load_processed()

    root = _repo_root()
    target = Path(output_path)
    if not target.is_absolute():
        target = root / target

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(_format_markdown(df), encoding="utf-8")
    return target


def main() -> int:
    try:
        target = generate_report()
        print(f"[INFO] Report geschrieben nach: {target}")
        return 0
    except FileNotFoundError:
        print("[ERROR] Processed CSV fehlt. Bitte zuerst python -m src.ingest ausfuehren")
        return 1
    except Exception as exc:  # pragma: no cover
        print(f"[ERROR] Report-Erstellung fehlgeschlagen: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
