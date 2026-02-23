# Job Application Analytics

## Projektziel
Dieses Repository analysiert Bewerbungsdaten aus einer Excel-Datei und stellt zentrale KPIs in einem Streamlit-Dashboard dar. Ziel ist ein reproduzierbares Showcase-Projekt fuer Bewerbungsprozesse.

## Projektstruktur
- `data/raw/`: Rohdaten (inkl. `Bewerbungsliste.xlsx`)
- `data/processed/`: aufbereitete Daten (`applications.csv`)
- `src/`: Ingestion- und KPI-Logik
- `dashboard/`: Streamlit-App
- `docs/`: KPI-Dokumentation
- `notebooks/`: explorative Analysen
- `screenshots/`: Dashboard-Screenshots
- `tests/`: Platz fuer Tests
- `.github/workflows/`: CI-Pipeline fuer Build- und Testchecks

## Showcase Features
- End-to-end Pipeline: Excel-Ingestion (`src/ingest.py`) nach `data/processed/applications.csv`
- Produktreifes Dashboard: KPI-Karten, Datenstand, Key Insights, Funnel, Export-Funktionen
- Data Quality: Required-Column-, Datums-, Status- und Duplicate-Checks in `src/quality.py`
- Reproduzierbarkeit: einfache Testskripte in `tests/` mit direkten `assert`-Checks
- CI-Absicherung: GitHub Actions Workflow (`.github/workflows/ci.yml`)
- Deployment-ready: Streamlit lokal oder per Docker/Docker Compose (Raspberry Pi geeignet)

## Architektur
```mermaid
flowchart LR
    subgraph Raw Layer
        A[data/raw/Bewerbungsliste.xlsx]
    end

    subgraph Processing Layer
        B[src/ingest.py]
        C[data/processed/applications.csv]
    end

    subgraph Analytics Layer
        D[src/kpi.py]
    end

    subgraph Presentation Layer
        E[dashboard/app.py (Streamlit)]
    end

    A --> B --> C --> D --> E
```

## Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Pipeline ausfuehren
```bash
python -m src.ingest
```

## Dashboard starten
```bash
streamlit run dashboard/app.py
```

## Daten aktualisieren
Im Dashboard links unter `Daten-Upload` eine neue Bewerbungsliste (`.xlsx`) hochladen.
Die Pipeline verarbeitet die Datei automatisch und aktualisiert die KPIs.

## Docker (Raspberry Pi)
```bash
docker compose build
docker compose up -d
```

Zugriff im Browser:
`http://<raspi-ip>:8501`

Hinweis:
- Auf dem Raspberry Pi ggf. `docker compose` statt `docker-compose` verwenden.
- Daten-Uploads im Dashboard werden im Volume unter `./data` persistiert.

## Nutzung
- Insight-Report erzeugen: `python -m src.report`
- Ergebnis: `reports/insights.md`

## Screenshots
- `screenshots/dashboard_overview.png` (Platzhalter)
- `screenshots/dashboard_funnel_and_insights.png` (Platzhalter)
- `screenshots/dashboard_quality_and_exports.png` (Platzhalter)

## KPI-Definitionen
Kurze Definitionen der berechneten Kennzahlen stehen in `docs/kpi_definition.md`.
Ergaenzt wurden u. a. Rueckmeldequote, Ghosting-Quote und Funnel-Conversion-Rates.

## Key Insights

- Interviewquote: X %
- Durchschnittliche Reaktionszeit: X Tage
- Höchste Conversion-Rate über Quelle: X
- Arbeitsmodell mit bester Erfolgsquote: X
- Korrelation Ranking Score vs. Interview: (positiv / schwach / keine)

Diese Analyse dient der datenbasierten Optimierung der Bewerbungsstrategie.
