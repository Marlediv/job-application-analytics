"""Streamlit dashboard for job application analytics."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.kpi import (
    active_applications,
    avg_wait_time,
    funnel_table,
    ghosted_count,
    ghosted_rate,
    interview_count,
    interview_rate,
    kpi_by_source,
    kpi_by_work_model,
    load_processed,
    ranking_vs_interview,
    rejection_count,
    rejection_rate,
    response_count,
    response_rate,
    total_applications,
    wait_time_by_status,
)


st.set_page_config(page_title="Job Application Analytics", layout="wide")
st.title("Job Application Analytics")


def _load_data() -> pd.DataFrame:
    return load_processed()


try:
    data = _load_data()
except Exception as exc:
    st.error(f"Daten konnten nicht geladen werden: {exc}")
    st.stop()

filtered = data.copy()

st.sidebar.header("Filter")

if "bewerbungsdatum" in filtered.columns:
    filtered["bewerbungsdatum"] = pd.to_datetime(filtered["bewerbungsdatum"], errors="coerce")
    valid_dates = filtered["bewerbungsdatum"].dropna()

    if not valid_dates.empty:
        start_date = valid_dates.min().date()
        end_date = valid_dates.max().date()
        selected_range = st.sidebar.date_input(
            "Zeitraum",
            value=(start_date, end_date),
            min_value=start_date,
            max_value=end_date,
        )
        if isinstance(selected_range, tuple) and len(selected_range) == 2:
            date_start, date_end = selected_range
            mask = filtered["bewerbungsdatum"].dt.date.between(date_start, date_end)
            filtered = filtered[mask]
else:
    st.sidebar.info("Kein Bewerbungsdatum vorhanden, Zeitfilter deaktiviert.")

if "quelle" in filtered.columns:
    source_options = sorted(filtered["quelle"].dropna().astype(str).str.strip().unique().tolist())
    selected_sources = st.sidebar.multiselect("Quelle", options=source_options, default=source_options)
    if selected_sources:
        filtered = filtered[filtered["quelle"].astype(str).str.strip().isin(selected_sources)]

if "arbeitsmodell" in filtered.columns:
    model_options = sorted(filtered["arbeitsmodell"].dropna().astype(str).str.strip().unique().tolist())
    selected_models = st.sidebar.multiselect(
        "Arbeitsmodell",
        options=model_options,
        default=model_options,
    )
    if selected_models:
        filtered = filtered[filtered["arbeitsmodell"].astype(str).str.strip().isin(selected_models)]

if "status" in filtered.columns:
    status_options = sorted(filtered["status"].dropna().astype(str).str.strip().unique().tolist())
    selected_status = st.sidebar.multiselect("Status", options=status_options, default=status_options)
    if selected_status:
        filtered = filtered[filtered["status"].astype(str).str.strip().isin(selected_status)]

top1, top2, top3, top4, top5, top6 = st.columns(6)
bottom1, bottom2, bottom3, bottom4, bottom5 = st.columns(5)

try:
    total_value = total_applications(filtered)
    active_value = active_applications(filtered)
    interview_value = interview_count(filtered)
    interview_rate_value = interview_rate(filtered)
    rejection_value = rejection_count(filtered)
    rejection_rate_value = rejection_rate(filtered)
    response_value = response_count(filtered)
    response_rate_value = response_rate(filtered)
    ghosted_value = ghosted_count(filtered)
    ghosted_rate_value = ghosted_rate(filtered)
    avg_wait_value = avg_wait_time(filtered) if "wartezeit_tage" in filtered.columns else float("nan")
    funnel_df = funnel_table(filtered)
except ValueError as exc:
    st.error(f"KPI-Berechnung nicht moeglich: {exc}")
    st.stop()

top1.metric("Gesamt", f"{total_value}")
top2.metric("Aktiv", f"{active_value}")
top3.metric("Interviews", f"{interview_value}")
top4.metric("Interviewquote", f"{interview_rate_value:.1%}")
top5.metric("Absagen", f"{rejection_value}")
top6.metric("Absagequote", f"{rejection_rate_value:.1%}")

bottom1.metric("Rueckmeldungen", f"{response_value}")
bottom2.metric("Rueckmeldequote", f"{response_rate_value:.1%}")
bottom3.metric("Ghosted", f"{ghosted_value}")
bottom4.metric("Ghosting-Quote", f"{ghosted_rate_value:.1%}")
bottom5.metric("Ø Wartezeit", "-" if pd.isna(avg_wait_value) else f"{avg_wait_value:.1f} Tage")

st.divider()

left, right = st.columns(2)

with left:
    st.subheader("Bewerbungen ueber Zeit")
    if "bewerbungsdatum" in filtered.columns and not filtered.empty:
        ts = filtered.copy()
        ts["bewerbungsdatum"] = pd.to_datetime(ts["bewerbungsdatum"], errors="coerce")
        ts = ts.dropna(subset=["bewerbungsdatum"])
        if not ts.empty:
            monthly = (
                ts.assign(monat=ts["bewerbungsdatum"].dt.to_period("M").dt.to_timestamp())
                .groupby("monat")
                .size()
                .reset_index(name="anzahl")
            )
            fig_time = px.bar(monthly, x="monat", y="anzahl", labels={"monat": "Monat", "anzahl": "Bewerbungen"})
            st.plotly_chart(fig_time, use_container_width=True)
        else:
            st.info("Keine gueltigen Datumswerte verfuegbar.")
    else:
        st.info("Spalte 'bewerbungsdatum' fehlt oder keine Daten vorhanden.")

with right:
    st.subheader("Funnel")
    if not funnel_df.empty:
        fig_funnel = go.Figure(go.Funnel(y=funnel_df["stage"], x=funnel_df["count"]))
        st.plotly_chart(fig_funnel, use_container_width=True)

        funnel_display = funnel_df.copy()
        funnel_display["rate_from_prev"] = funnel_display["rate_from_prev"].map(
            lambda v: "-" if pd.isna(v) else f"{v:.1%}"
        )
        funnel_display["rate_from_total"] = funnel_display["rate_from_total"].map(lambda v: f"{v:.1%}")
        st.dataframe(funnel_display, use_container_width=True)
    else:
        st.info("Keine Funnel-Daten verfuegbar.")

left2, right2 = st.columns(2)

with left2:
    st.subheader("Interviewquote nach Quelle")
    try:
        source_kpi = kpi_by_source(filtered)
        if not source_kpi.empty:
            fig_source = px.bar(
                source_kpi,
                x="quelle",
                y="interview_rate",
                hover_data=["counts"],
                labels={"quelle": "Quelle", "interview_rate": "Interviewquote"},
            )
            fig_source.update_yaxes(tickformat=".0%")
            st.plotly_chart(fig_source, use_container_width=True)
        else:
            st.info("Keine Daten fuer Quelle vorhanden.")
    except ValueError as exc:
        st.info(str(exc))

with right2:
    st.subheader("Wartezeit nach Status")
    try:
        wait_kpi = wait_time_by_status(filtered)
        if not wait_kpi.empty:
            fig_wait = px.bar(
                wait_kpi,
                x="status",
                y="avg_wait",
                hover_data=["median_wait", "counts"],
                labels={"status": "Status", "avg_wait": "Ø Wartezeit (Tage)"},
            )
            st.plotly_chart(fig_wait, use_container_width=True)
        else:
            st.info("Keine Wartezeit-Daten verfuegbar.")
    except ValueError as exc:
        st.info(str(exc))

st.subheader("Ghosting nach Quelle")
if "quelle" in filtered.columns:
    try:
        source_ghost = filtered.copy()
        source_ghost["quelle"] = source_ghost["quelle"].fillna("Unbekannt").astype(str).str.strip()
        source_ghost = (
            source_ghost.groupby("quelle", dropna=False)
            .agg(counts=("quelle", "size"), ghosted=("is_ghosted", "sum"))
            .reset_index()
        )
        source_ghost["ghosted_rate"] = source_ghost["ghosted"] / source_ghost["counts"]
        source_ghost = source_ghost.sort_values("counts", ascending=False)

        fig_ghost = px.bar(
            source_ghost,
            x="quelle",
            y="ghosted_rate",
            hover_data=["counts", "ghosted"],
            labels={"quelle": "Quelle", "ghosted_rate": "Ghosting-Quote"},
        )
        fig_ghost.update_yaxes(tickformat=".0%")
        st.plotly_chart(fig_ghost, use_container_width=True)
    except Exception as exc:  # pragma: no cover
        st.info(f"Ghosting-Auswertung nicht verfuegbar: {exc}")
else:
    st.info("Spalte 'quelle' fehlt, Ghosting nach Quelle nicht verfuegbar.")

st.subheader("Ranking Score vs Interview")
try:
    ranking_df = ranking_vs_interview(filtered)
    if not ranking_df.empty:
        fig_scatter = px.scatter(
            ranking_df,
            x="ranking_score",
            y="interviewed",
            color="interviewed",
            labels={"ranking_score": "Ranking Score", "interviewed": "Interviewed"},
            opacity=0.7,
        )
        st.plotly_chart(fig_scatter, use_container_width=True)
    else:
        st.info("Keine gueltigen Ranking Scores vorhanden.")
except ValueError as exc:
    st.info(str(exc))

st.subheader("KPI nach Arbeitsmodell")
try:
    model_kpi = kpi_by_work_model(filtered)
    if not model_kpi.empty:
        st.dataframe(model_kpi, use_container_width=True)
except ValueError as exc:
    st.info(str(exc))
