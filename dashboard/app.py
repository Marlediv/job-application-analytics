"""Streamlit dashboard for job application analytics."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.kpi import (
    active_applications,
    avg_wait_time,
    interview_count,
    interview_rate,
    kpi_by_source,
    kpi_by_work_model,
    load_processed,
    ranking_vs_interview,
    rejection_count,
    rejection_rate,
    total_applications,
    wait_time_by_status,
)


st.set_page_config(page_title="Job Application Analytics", layout="wide")
st.title("Job Application Analytics")


def _load_data() -> pd.DataFrame:
    return load_processed()


def _status_series(df: pd.DataFrame) -> pd.Series:
    if "status" not in df.columns:
        return pd.Series([""] * len(df), index=df.index)

    status = df["status"].fillna("").astype(str).str.strip().str.lower()
    status = (
        status.str.replace("ä", "ae", regex=False)
        .str.replace("ö", "oe", regex=False)
        .str.replace("ü", "ue", regex=False)
        .str.replace("ß", "ss", regex=False)
    )
    return status


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

col1, col2, col3, col4, col5, col6, col7 = st.columns(7)

try:
    total_value = total_applications(filtered)
    active_value = active_applications(filtered)
    interview_value = interview_count(filtered)
    interview_rate_value = interview_rate(filtered)
    rejection_value = rejection_count(filtered)
    rejection_rate_value = rejection_rate(filtered)
    avg_wait_value = avg_wait_time(filtered) if "wartezeit_tage" in filtered.columns else float("nan")
except ValueError as exc:
    st.error(f"KPI-Berechnung nicht moeglich: {exc}")
    st.stop()

col1.metric("Gesamt", f"{total_value}")
col2.metric("Aktiv", f"{active_value}")
col3.metric("Interviews", f"{interview_value}")
col4.metric("Interviewquote", f"{interview_rate_value:.1%}")
col5.metric("Absagen", f"{rejection_value}")
col6.metric("Absagequote", f"{rejection_rate_value:.1%}")
col7.metric("Ø Wartezeit", "-" if pd.isna(avg_wait_value) else f"{avg_wait_value:.1f} Tage")

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
    if "status" in filtered.columns:
        status_norm = _status_series(filtered)
        total_stage = len(filtered)
        feedback_stage = int(
            status_norm.str.contains(r"rueckmeldung|feedback|antwort|interview|angebot|absage|abgelehnt", regex=True).sum()
        )
        interview_stage = int(status_norm.str.contains(r"interview|gespraech", regex=True).sum())
        offer_stage = int(status_norm.str.contains(r"angebot|offer|zusage", regex=True).sum())

        stages = ["Bewerbung"]
        values = [total_stage]

        if feedback_stage > 0:
            stages.append("Rueckmeldung")
            values.append(feedback_stage)
        if interview_stage > 0:
            stages.append("Interview")
            values.append(interview_stage)
        if offer_stage > 0:
            stages.append("Angebot")
            values.append(offer_stage)

        fig_funnel = go.Figure(go.Funnel(y=stages, x=values))
        st.plotly_chart(fig_funnel, use_container_width=True)
    else:
        st.info("Spalte 'status' fehlt, Funnel nicht ableitbar.")

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
