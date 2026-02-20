# KPI-Definitionen

Hinweis: Status-Matching ist case-insensitive und basiert auf `contains`.

## Gesamtbewerbungen
Anzahl aller Zeilen im aufbereiteten Datensatz.

## Aktive Bewerbungen
Anzahl Bewerbungen mit Status, der nicht auf Absage oder Angebot schliessen laesst.

## Interviews
Anzahl Bewerbungen mit Status-Text, der `Interview` oder `Gespraech` enthaelt.

## Interviewquote
Formel: `Interviews / Gesamtbewerbungen`.

## Absagen
Anzahl Bewerbungen mit Status-Text, der auf Absage hindeutet.

## Absagequote
Formel: `Absagen / Gesamtbewerbungen`.

## Durchschnittliche Wartezeit
Mittelwert der numerischen Spalte `wartezeit_tage`.

## KPI nach Quelle
Gruppierung nach Quelle mit Anzahl Bewerbungen und Interviewquote je Quelle.

## KPI nach Arbeitsmodell
Gruppierung nach Arbeitsmodell mit Anzahl Bewerbungen und Interviewquote je Arbeitsmodell.

## Wartezeit nach Status
Gruppierung nach Status mit Durchschnitts- und Median-Wartezeit.

## Ranking vs. Interview
Datensatz fuer Scatter-Plot aus `ranking_score` und einem abgeleiteten Boolean `interviewed`.
