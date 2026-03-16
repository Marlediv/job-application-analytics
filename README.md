# Job Application Analytics
[![CI](https://github.com/Marlediv/job-application-analytics/actions/workflows/ci.yml/badge.svg)](https://github.com/Marlediv/job-application-analytics/actions/workflows/ci.yml)
![Python 3.13](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)

End-to-End Analytics Pipeline zur Analyse des Bewerbungsprozesses.
Fokus auf Data Ingestion, Data Quality, KPI-Design, Insight-Engine,
CI/CD und containerisiertem Deployment auf Raspberry Pi.

## Showcase Features
- Ingestion & Schema-Normalisierung (Synonym-Mapping, Trim, Typkonvertierung)
- Data Quality Layer (Required Columns, Date Checks, Duplicates, Status Validation)
- KPI Layer mit zentraler Status-Normalisierung, Funnel-Conversion & Ghosting-Metriken
- Insight-Engine mit automatischen Business-Callouts und Hervorhebung des Unternehmens mit der längsten Wartezeit ohne Antwort
- Markdown Report Export
- Robuste Fallback-Charts
- Docker Deployment (Raspi) mit persistentem Volume
- GitHub Actions CI (Compile + Tests)

## Quickstart (Docker)
```bash
git clone https://github.com/Marlediv/job-application-analytics.git
cd job-application-analytics
docker compose up -d --build
```

Aufruf:
`http://<raspi-ip>:8501`

## Quickstart (lokal)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m src.ingest
streamlit run dashboard/app.py
```

## Architektur
![Architektur](docs/architecture.png)

Source of Truth ist `docs/architecture.mmd`, `docs/architecture.png` wird daraus gerendert.

Lokale Generierung:
```bash
npx -y @mermaid-js/mermaid-cli -i docs/architecture.mmd -o docs/architecture.png -b transparent
```

```mermaid
flowchart LR
    User[Browser User]
    Excel[Excel Upload]
    Streamlit[Streamlit App<br>Docker Container]
    Raw[data/raw]
    Ingest[src.ingest]
    Processed[data/processed/applications.csv]
    KPI[src.kpi]
    Insights[src.insights]
    Report[src.report]
    CI[GitHub Actions CI]
    Volume[(Docker Volume ./data:/app/data)]

    User --> Excel
    Excel --> Streamlit
    Streamlit --> Raw
    Raw --> Ingest
    Ingest --> Processed
    Processed --> KPI
    KPI --> Insights
    Insights --> Streamlit
    Insights --> Report
    CI --> Ingest
    Volume --- Raw
    Volume --- Processed
```

## Datenfluss
1. Excel wird hochgeladen (oder in `data/raw` abgelegt).
2. Ingestion normalisiert + validiert Daten.
3. Processed CSV wird erzeugt.
4. KPI- und Insight-Layer speisen das Dashboard.

## Screenshots
![Dashboard Overview](screenshots/dashboard_overview.png)
![Funnel and Insights](screenshots/funnel_and_insights.png)
![Export and DQ](screenshots/export_and_dq.png)

## Datenformat & Schema (Data Contract)
- Das Dashboard erwartet eine strukturierte Excel-Datei.
- Spalten werden in der Ingestion normalisiert (inkl. Synonyme und Typen).
- Fehlende Pflichtspalten führen zu einem DQ-FAIL.
- Die Excel-Datei benötigt eine Headerzeile mit den Spaltennamen; das Sheet wird automatisch erkannt (erstes sinnvolles Sheet).

| Spalte | Typ | Pflicht | Beschreibung |
| --- | --- | --- | --- |
| bewerbungsdatum | Datum | Ja | Datum der Bewerbung |
| unternehmen | String | Ja | Firmenname |
| stelle | String | Ja | Position |
| quelle | String | Ja | Bewerbungsquelle |
| status | String | Ja | Prozessstatus |
| arbeitsmodell | String | Nein | remote/hybrid/onsite |
| ranking_score | Float | Nein | Eigene Bewertung (0-1) |
| wartezeit_tage | Integer | Nein | Wartezeit |

Wichtige Regeln:
- Erlaubte Statuswerte (Muster): `absage`, `abgelehnt`, `interview`, `gespräch`, `angebot`, `offer`, `zusage`, `eingangsbestätigung`, `antwort`, `rückmeldung`.
- Unbekannte Statuswerte führen zu `WARN` (Pipeline läuft weiter).
- Missing Required Columns führen zu `FAIL` (Pipeline stoppt).
- Dashboard/KPI normalisieren Status konsistent (`status_clean` + `status_canonical`) und mappen Schreibvarianten auf kanonische Werte.
- Für offene Bewerbungen wird die Wartezeit dynamisch auf Basis von `bewerbungsdatum` bzw. `letzter_kontakt` berechnet, wenn `wartezeit_tage` nicht gepflegt ist.
- Ghosting wird erkannt, wenn der Status `Keine Rückmeldung` vorliegt oder bei offenen Bewerbungen länger als 21 Tage keine Reaktion erfolgt.
- Ranking-Analyse zeigt die Verteilung von `ranking_score` nach Bewerbungsstatus (statt Boolean-Interview-Flag).

Referenzstruktur: `docs/example_schema.csv`.

## Data Quality Checks
- Required Column Check
- Date Validation (keine Future-Dates)
- Duplicate Detection
- Status Validation

Verhalten:
- `FAIL` stoppt die Pipeline.
- `WARN` protokolliert einen Hinweis, Verarbeitung läuft weiter.

## Reproduzierbarkeit
- CI Workflow: `.github/workflows/ci.yml`
- Compile-Checks: `python -m compileall src dashboard`
- Low-friction Tests (ohne pytest): `tests/test_kpi_flags.py`, `tests/test_rate_by_source.py`, `tests/test_quality.py`

## Lokale Nutzung
```bash
python -m src.ingest
streamlit run dashboard/app.py
```

## Docker (Raspberry Pi)
```bash
docker compose up -d --build
```

Zugriff:
`http://<raspi-ip>:8501`

## Privacy Note
Hinweis: Keine personenbezogenen Daten ins Repo committen. `data/raw` und `data/processed` bleiben lokal via Volume.

## Report-Export
```bash
python -m src.report
```
Ausgabe:
`reports/insights.md`

## Projektstruktur
- `dashboard/`: Streamlit-App
- `src/`: Ingestion, DQ, KPI, Insights, Report
- `data/raw/`: Excel-Uploads
- `data/processed/`: aufbereitete CSV (`applications.csv`)
- `docs/`: Architektur, Schema-Beispiel, KPI-Doku
- `reports/`: generierte Reports
- `tests/`: testbare Skripte via `python tests/<datei>.py`
- `.github/workflows/`: CI-Pipeline

## Roadmap
- PostgreSQL Backend
- Authentifizierung / Basic Auth
- Scheduled Ingestion
- PDF Export
- Multi-User Tracking
