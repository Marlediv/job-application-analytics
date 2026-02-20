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

## KPI-Definitionen
Kurze Definitionen der berechneten Kennzahlen stehen in `docs/kpi_definition.md`.

## Key Insights

- Interviewquote: X %
- Durchschnittliche Reaktionszeit: X Tage
- Höchste Conversion-Rate über Quelle: X
- Arbeitsmodell mit bester Erfolgsquote: X
- Korrelation Ranking Score vs. Interview: (positiv / schwach / keine)

Diese Analyse dient der datenbasierten Optimierung der Bewerbungsstrategie.
