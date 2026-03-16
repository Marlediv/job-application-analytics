"""Streamlit dashboard for job application analytics."""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.kpi import (
    STATUS_ORDER,
    active_applications,
    avg_wait_time,
    funnel_table,
    ghosted_count,
    ghosted_rate,
    interview_count,
    interview_rate,
    kpi_by_work_model,
    load_processed,
    rate_by_source,
    rejection_count,
    rejection_rate,
    response_count,
    response_rate,
    total_applications,
    wait_time_by_status,
)
from src.insights import build_key_insights, format_insights_markdown
from src.report import REPORT_PATH, generate_report


st.set_page_config(page_title="Job Application Analytics", layout="wide")

RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
RAW_FILE = RAW_DIR / "Bewerbungsliste.xlsx"
PROCESSED_FILE = PROCESSED_DIR / "applications.csv"


def _load_data() -> pd.DataFrame:
    return load_processed()


def render_kpi(label: str, value: str, help_text: str | None = None) -> None:
    st.metric(label, value)
    if help_text:
        st.caption(help_text)


def apply_chart_layout(fig: go.Figure) -> go.Figure:
    fig.update_layout(height=340, margin=dict(l=20, r=20, t=50, b=30))
    return fig


def _dataset_timestamp() -> str:
    if PROCESSED_FILE.exists():
        mtime = datetime.fromtimestamp(PROCESSED_FILE.stat().st_mtime).astimezone()
        return mtime.strftime("%Y-%m-%d %H:%M:%S %Z")
    return "-"


def _host_badge() -> str:
    try:
        return os.uname().nodename
    except AttributeError:  # pragma: no cover
        return "unknown-host"


st.sidebar.header("Daten-Upload")
uploaded_file = st.sidebar.file_uploader("Neue Bewerbungsliste (.xlsx)", type=["xlsx"])

if uploaded_file is not None:
    upload_bytes = uploaded_file.getvalue()
    upload_hash = hashlib.sha256(upload_bytes).hexdigest()

    if st.session_state.get("last_upload_hash") != upload_hash:
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        RAW_FILE.write_bytes(upload_bytes)

        try:
            result = subprocess.run(
                [sys.executable, "-m", "src.ingest"],
                check=True,
                capture_output=True,
                text=True,
            )
            st.session_state["last_upload_hash"] = upload_hash
            st.session_state["last_update_timestamp"] = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
            st.sidebar.success("Upload erfolgreich. Daten wurden verarbeitet.")
            if result.stdout.strip():
                st.sidebar.code(result.stdout.strip(), language="text")
            st.cache_data.clear()
            st.rerun()
        except subprocess.CalledProcessError as exc:
            err_text = (exc.stderr or exc.stdout or str(exc)).strip()
            short_error = err_text.splitlines()[-1] if err_text else str(exc)
            st.sidebar.error(f"Ingestion fehlgeschlagen: {short_error}")
            if exc.stdout.strip():
                st.sidebar.code(exc.stdout.strip(), language="text")
            if exc.stderr.strip():
                st.sidebar.code(exc.stderr.strip(), language="text")

if "last_update_timestamp" in st.session_state:
    st.sidebar.caption(f"Letztes Update: {st.session_state['last_update_timestamp']}")


try:
    data = _load_data()
except FileNotFoundError:
    st.info("Bitte Excel hochladen oder zuerst python -m src.ingest ausführen.")
    st.stop()
except Exception as exc:
    st.error(f"Daten konnten nicht geladen werden: {exc}")
    st.stop()

head_left, head_right = st.columns([3, 2])
with head_left:
    st.title("Job Application Analytics")
with head_right:
    st.markdown(f"**Datenstand:** {_dataset_timestamp()}")
    st.markdown(f"**Datensatz:** `applications.csv` ({len(data)} Zeilen)")
    st.caption(f"RUNNING ON: `{_host_badge()}`")

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

if "interviewed_flag" not in filtered.columns:
    filtered["interviewed_flag"] = filtered.get("is_interview", False)
if "ghosted_flag" not in filtered.columns:
    filtered["ghosted_flag"] = filtered.get("is_ghosted", False)

st.sidebar.header("Export")
if st.sidebar.button("Insight-Report (MD) erzeugen"):
    try:
        report_path = generate_report(REPORT_PATH)
        report_content = Path(report_path).read_text(encoding="utf-8")
        st.session_state["insight_report_content"] = report_content
        st.sidebar.success("Insight-Report wurde erzeugt.")
    except Exception as exc:
        st.sidebar.error(f"Report-Erzeugung fehlgeschlagen: {exc}")

if "insight_report_content" in st.session_state:
    st.sidebar.download_button(
        "Insight-Report (MD) herunterladen",
        data=st.session_state["insight_report_content"],
        file_name="insights.md",
        mime="text/markdown",
    )

snapshot_csv = filtered.to_csv(index=False).encode("utf-8")
st.sidebar.download_button(
    "KPI Snapshot (CSV)",
    data=snapshot_csv,
    file_name="kpi_snapshot_filtered.csv",
    mime="text/csv",
)

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
    avg_wait_value = avg_wait_time(filtered)
    funnel_df = funnel_table(filtered)
except ValueError as exc:
    st.error(f"KPI-Berechnung nicht möglich: {exc}")
    st.stop()

top1, top2, top3, top4, top5, top6 = st.columns(6)
with top1:
    render_kpi("Gesamt", f"{total_value}")
with top2:
    render_kpi("Aktiv", f"{active_value}")
with top3:
    render_kpi("Rückmeldungen", f"{response_value}")
with top4:
    render_kpi("Interviews", f"{interview_value}")
with top5:
    render_kpi("Absagen", f"{rejection_value}")
with top6:
    render_kpi("Ghosted", f"{ghosted_value}")

bottom1, bottom2, bottom3, bottom4, bottom5 = st.columns(5)
with bottom1:
    render_kpi("Rückmeldequote", f"{response_rate_value:.1%}")
with bottom2:
    render_kpi("Interviewquote", f"{interview_rate_value:.1%}")
with bottom3:
    render_kpi("Absagequote", f"{rejection_rate_value:.1%}")
with bottom4:
    render_kpi("Ghosting-Quote", f"{ghosted_rate_value:.1%}")
with bottom5:
    render_kpi("Ø Wartezeit", "-" if pd.isna(avg_wait_value) else f"{avg_wait_value:.1f} Tage")

st.subheader("Key Insights")
insights = build_key_insights(filtered, funnel_df=funnel_df)
icon_cycle = ["🧭", "📉", "⏳", "✅", "⚠️", "📌"]
insight_lines = [f"{icon_cycle[idx % len(icon_cycle)]} {text}" for idx, text in enumerate(insights)]
st.markdown(format_insights_markdown(insight_lines))

st.divider()

left, right = st.columns(2)

with left:
    st.subheader("Bewerbungen über Zeit")
    if filtered.empty:
        st.info("Keine Daten für die aktuelle Filterauswahl.")
    elif "bewerbungsdatum" in filtered.columns:
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
            apply_chart_layout(fig_time)
            fig_time.update_yaxes(rangemode="tozero", tickformat=",d")
            st.plotly_chart(fig_time, use_container_width=True, key="applications_over_time_chart")
        else:
            st.info("Keine Daten für die aktuelle Filterauswahl.")
    else:
        st.info("Spalte 'bewerbungsdatum' fehlt oder keine Daten vorhanden.")

with right:
    st.subheader("Funnel")
    if filtered.empty:
        st.info("Keine Daten für die aktuelle Filterauswahl.")
    elif not funnel_df.empty:
        fig_funnel = go.Figure(go.Funnel(y=funnel_df["stage"], x=funnel_df["count"]))
        apply_chart_layout(fig_funnel)
        st.plotly_chart(fig_funnel, use_container_width=True, key="funnel_chart")

        st.caption("Conversion-Tabelle")
        funnel_display = funnel_df.copy()
        funnel_display["rate_from_prev"] = funnel_display["rate_from_prev"].map(
            lambda v: "-" if pd.isna(v) else f"{v:.1%}"
        )
        funnel_display["rate_from_total"] = funnel_display["rate_from_total"].map(lambda v: f"{v:.1%}")
        st.dataframe(funnel_display, use_container_width=True)
    else:
        st.info("Keine Daten für die aktuelle Filterauswahl.")

st.divider()

left2, right2 = st.columns(2)

with left2:
    st.subheader("Interviewquote nach Quelle")
    if filtered.empty:
        st.info("Keine Daten für die aktuelle Filterauswahl.")
    elif "quelle" not in filtered.columns:
        st.info("Spalte 'quelle' fehlt, Interviewquote nach Quelle nicht verfügbar.")
    else:
        try:
            counts_by_source = (
                filtered.assign(quelle=filtered["quelle"].astype("string").str.strip())
                .loc[lambda d: d["quelle"].notna() & d["quelle"].ne("")]
                .groupby("quelle", dropna=False)
                .size()
                .reset_index(name="counts")
                .sort_values(["counts", "quelle"], ascending=[False, True])
            )
            source_rates = rate_by_source(filtered, "interviewed_flag")
            flagged_sum = pd.to_numeric(source_rates["flagged"], errors="coerce").fillna(0).sum() if not source_rates.empty else 0

            if source_rates.empty or source_rates["counts"].sum() == 0 or counts_by_source.empty:
                st.info("Keine Daten für die aktuelle Filterauswahl.")
            elif interview_value == 0 or flagged_sum == 0:
                st.info("Keine Interviews in der aktuellen Auswahl. Stattdessen: Bewerbungen nach Quelle.")
                fig_counts = px.bar(
                    counts_by_source,
                    x="quelle",
                    y="counts",
                    hover_data={"quelle": True, "counts": True},
                    labels={"quelle": "Quelle", "counts": "Bewerbungen"},
                    title="Bewerbungen nach Quelle",
                )
                apply_chart_layout(fig_counts)
                fig_counts.update_yaxes(rangemode="tozero", tickformat=",d")
                st.plotly_chart(fig_counts, use_container_width=True, key="interview_count_by_source_chart")
            else:
                fig_source = px.bar(
                    source_rates,
                    x="quelle",
                    y="rate",
                    hover_data={"quelle": True, "counts": True, "rate": ":.0%"},
                    labels={"quelle": "Quelle", "rate": "Interviewquote"},
                )
                apply_chart_layout(fig_source)
                fig_source.update_yaxes(tickformat=".0%", range=[0, 1])
                st.plotly_chart(fig_source, use_container_width=True, key="interview_rate_by_source_chart")
        except ValueError as exc:
            st.info(str(exc))

with right2:
    st.subheader("Wartezeit nach Status")
    if filtered.empty:
        st.info("Keine Daten für die aktuelle Filterauswahl.")
    else:
        try:
            wait_kpi = wait_time_by_status(filtered)
            if not wait_kpi.empty:
                wait_kpi = wait_kpi.rename(columns={"status": "status_canonical"})
                extra_statuses = [
                    s for s in wait_kpi["status_canonical"].dropna().unique().tolist() if s not in STATUS_ORDER
                ]
                status_order = STATUS_ORDER + extra_statuses
                wait_display = (
                    wait_kpi.set_index("status_canonical")
                    .reindex(status_order)
                    .reset_index()
                    .rename(columns={"index": "status_canonical"})
                )
                wait_display["counts"] = wait_display["counts"].fillna(0).astype(int)
                wait_display["valid_wait_count"] = wait_display["valid_wait_count"].fillna(0).astype(int)
                no_wait_data = wait_display["valid_wait_count"].eq(0)
                wait_display.loc[no_wait_data, "avg_wait"] = wait_display.loc[no_wait_data, "avg_wait"].fillna(0.0)
                wait_display.loc[no_wait_data, "median_wait"] = wait_display.loc[no_wait_data, "median_wait"].fillna(0.0)
                fig_wait = px.bar(
                    wait_display,
                    x="status_canonical",
                    y="avg_wait",
                    hover_data=["median_wait", "counts", "valid_wait_count"],
                    labels={"status_canonical": "Status", "avg_wait": "Ø Wartezeit (Tage)"},
                )
                apply_chart_layout(fig_wait)
                st.plotly_chart(fig_wait, use_container_width=True, key="waiting_time_by_status_chart")
            else:
                st.info("Keine Daten für die aktuelle Filterauswahl.")
        except ValueError as exc:
            st.info(str(exc))

st.divider()

left3, right3 = st.columns(2)

with left3:
    st.subheader("Ghosting nach Quelle")
    if filtered.empty:
        st.info("Keine Daten für die aktuelle Filterauswahl.")
    elif "quelle" in filtered.columns:
        try:
            counts_by_source = (
                filtered.assign(quelle=filtered["quelle"].astype("string").str.strip())
                .loc[lambda d: d["quelle"].notna() & d["quelle"].ne("")]
                .groupby("quelle", dropna=False)
                .size()
                .reset_index(name="counts")
                .sort_values(["counts", "quelle"], ascending=[False, True])
            )
            source_rates = rate_by_source(filtered, "ghosted_flag")
            flagged_sum = pd.to_numeric(source_rates["flagged"], errors="coerce").fillna(0).sum() if not source_rates.empty else 0

            if source_rates.empty or source_rates["counts"].sum() == 0 or counts_by_source.empty:
                st.info("Keine Daten für die aktuelle Filterauswahl.")
            elif ghosted_value == 0 or flagged_sum == 0:
                st.info("Kein Ghosting in der aktuellen Auswahl. Stattdessen: Bewerbungen nach Quelle.")
                fig_counts = px.bar(
                    counts_by_source,
                    x="quelle",
                    y="counts",
                    hover_data={"quelle": True, "counts": True},
                    labels={"quelle": "Quelle", "counts": "Bewerbungen"},
                    title="Bewerbungen nach Quelle",
                )
                apply_chart_layout(fig_counts)
                fig_counts.update_yaxes(rangemode="tozero", tickformat=",d")
                st.plotly_chart(fig_counts, use_container_width=True, key="ghosting_count_by_source_chart")
            else:
                fig_ghost = px.bar(
                    source_rates,
                    x="quelle",
                    y="rate",
                    hover_data={"quelle": True, "counts": True, "rate": ":.0%"},
                    labels={"quelle": "Quelle", "rate": "Ghosting-Quote"},
                )
                apply_chart_layout(fig_ghost)
                fig_ghost.update_yaxes(tickformat=".0%", range=[0, 1])
                st.plotly_chart(fig_ghost, use_container_width=True, key="ghosting_rate_by_source_chart")
        except Exception as exc:  # pragma: no cover
            st.info(f"Ghosting-Auswertung nicht verfügbar: {exc}")
    else:
        st.info("Spalte 'quelle' fehlt, Ghosting nach Quelle nicht verfügbar.")

with right3:
    st.subheader("Ranking")
    if filtered.empty:
        st.info("Keine Daten für die aktuelle Filterauswahl.")
    else:
        if "ranking_score" not in filtered.columns:
            st.info("Kein Ranking Score vorhanden – bitte Spalte 'ranking_score' pflegen, um dieses Diagramm zu nutzen.")
        else:
            ranking_plot = filtered.copy()
            ranking_plot["ranking_score"] = pd.to_numeric(ranking_plot["ranking_score"], errors="coerce")
            if "status_canonical" not in ranking_plot.columns:
                ranking_plot["status_canonical"] = ranking_plot.get("status", "Unbekannt")
            ranking_plot["status_canonical"] = (
                ranking_plot["status_canonical"].fillna("Unbekannt").astype(str).str.strip().replace("", "Unbekannt")
            )
            ranking_plot = ranking_plot.dropna(subset=["ranking_score"])

            if ranking_plot.empty:
                st.info("Keine Daten für die aktuelle Filterauswahl.")
            else:
                ordered_status = STATUS_ORDER + [
                    s for s in ranking_plot["status_canonical"].dropna().unique().tolist() if s not in STATUS_ORDER
                ]
                hover_cols: list[str] = []
                if "unternehmen" in ranking_plot.columns:
                    hover_cols.append("unternehmen")
                if "stelle" in ranking_plot.columns:
                    hover_cols.append("stelle")

                fig_scatter = px.scatter(
                    ranking_plot,
                    x="ranking_score",
                    y="status_canonical",
                    color="status_canonical",
                    category_orders={"status_canonical": ordered_status},
                    labels={"ranking_score": "Ranking Score", "status_canonical": "Status"},
                    hover_data=hover_cols if hover_cols else None,
                    opacity=0.65,
                )
                apply_chart_layout(fig_scatter)
                fig_scatter.update_yaxes(type="category")
                st.plotly_chart(fig_scatter, use_container_width=True, key="ranking_scatter_chart")

st.divider()

st.subheader("KPI nach Arbeitsmodell")
if filtered.empty:
    st.info("Keine Daten für die aktuelle Filterauswahl.")
else:
    try:
        model_kpi = kpi_by_work_model(filtered)
        if not model_kpi.empty:
            st.dataframe(model_kpi, use_container_width=True)
        else:
            st.info("Keine Daten für die aktuelle Filterauswahl.")
    except ValueError as exc:
        st.info(str(exc))
