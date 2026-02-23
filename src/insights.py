"""Helpers for short, user-facing insight bullets."""

from __future__ import annotations

from typing import Iterable

import pandas as pd

from .kpi import funnel_table, ghosted_rate, interview_count, wait_time_by_status


def _top_source_by_applications(df: pd.DataFrame) -> str:
    if "quelle" not in df.columns:
        return "Top-Quelle nach Bewerbungen: keine Quelle im Datensatz vorhanden."

    grouped = (
        df.assign(quelle=df["quelle"].astype("string").str.strip())
        .loc[lambda d: d["quelle"].notna() & d["quelle"].ne("")]
        .groupby("quelle")
        .size()
        .reset_index(name="counts")
        .sort_values(["counts", "quelle"], ascending=[False, True])
    )
    if grouped.empty:
        return "Top-Quelle nach Bewerbungen: keine verwertbaren Quellen vorhanden."

    top = grouped.iloc[0]
    return f"Top-Quelle nach Bewerbungen: `{top['quelle']}` (n={int(top['counts'])})."


def _funnel_bottleneck(df: pd.DataFrame, funnel_df: pd.DataFrame | None = None) -> str:
    table = funnel_df if funnel_df is not None else funnel_table(df)
    if table.empty or "rate_from_prev" not in table.columns:
        return "Funnel-Engpass: nicht berechenbar."

    drops = table.dropna(subset=["rate_from_prev"])
    if drops.empty:
        return "Funnel-Engpass: nicht berechenbar."

    bottleneck = drops.sort_values("rate_from_prev", ascending=True).iloc[0]
    return (
        f"Groesster Funnel-Drop vor Stufe `{bottleneck['stage']}` "
        f"mit Conversion {float(bottleneck['rate_from_prev']):.1%}."
    )


def _highest_wait_status(df: pd.DataFrame) -> str:
    if "status" not in df.columns or "wartezeit_tage" not in df.columns:
        return "Status mit hoechster Ø Wartezeit: nicht verfuegbar."

    wait_df = wait_time_by_status(df)
    if wait_df.empty:
        return "Status mit hoechster Ø Wartezeit: nicht verfuegbar."

    top = wait_df.sort_values("avg_wait", ascending=False).iloc[0]
    return (
        f"Status mit hoechster Ø Wartezeit: `{top['status']}` "
        f"({float(top['avg_wait']):.1f} Tage, n={int(top['counts'])})."
    )


def build_key_insights(
    df: pd.DataFrame,
    funnel_df: pd.DataFrame | None = None,
    ghosting_warn_threshold: float = 0.2,
) -> list[str]:
    insights: list[str] = [
        _top_source_by_applications(df),
        _funnel_bottleneck(df, funnel_df=funnel_df),
        _highest_wait_status(df),
    ]

    interviews = interview_count(df)
    if interviews == 0:
        insights.append("Keine Interviews in der Auswahl. Empfehlung: CV/Titel-Targeting und Quellenmix nachschaerfen.")
    else:
        insights.append(f"Interviews vorhanden: {interviews} (Conversion sichtbar messbar).")

    g_rate = ghosted_rate(df)
    if g_rate > ghosting_warn_threshold:
        insights.append(f"Ghosting-Quote ist erhoeht ({g_rate:.1%}). Empfehlung: Follow-up-Playbook straffen.")
    else:
        insights.append(f"Ghosting-Quote im unkritischen Bereich ({g_rate:.1%}).")

    return insights


def format_insights_markdown(insights: Iterable[str]) -> str:
    return "\n".join(f"- {line}" for line in insights)
