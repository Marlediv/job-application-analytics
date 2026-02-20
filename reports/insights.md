# Key Insights Report

Erstellt am: 2026-02-20 18:31:17 CET

## KPI Summary

| KPI | Wert |
| --- | --- |
| Gesamtbewerbungen | 14 |
| Aktive Bewerbungen | 4 |
| Rueckmeldungen | 14 |
| Rueckmeldequote | 100.0% |
| Interviews | 0 |
| Interviewquote | 0.0% |
| Absagen | 10 |
| Absagequote | 71.4% |
| Ghosted | 0 |
| Ghosting-Quote | 0.0% |
| Durchschnittliche Wartezeit | 7.2 Tage |

## Key Insights

- Top-Quelle nach Rueckmeldequote: `Firmenportal` (100.0%, n=11).
- Top-Quelle nach Interviewquote: `Firmenportal` (0.0%, n=11).
- Status mit hoechster medianer Wartezeit: `Absage` (7.5 Tage, n=10).
- Ghosting: 0 Bewerbungen (0.0%) gelten als ghosted. Empfehlung: spaetestens nach 14 Tagen aktiv nachfassen.
- Noch keine Interviews im Datensatz.

## Methodik

- Status-Flags werden zentral in `src.kpi._ensure_status_flags` normiert (case-insensitive Matching).
- `is_response` erfasst Rueckmeldung/Antwort sowie Absage, Angebot und Interview als Reaktionsereignisse.
- Ghosting ist definiert als `is_active == True` und `wartezeit_tage >= 30`.
- Wenn `wartezeit_tage` fehlt, wird Ghosting als 0 behandelt.
