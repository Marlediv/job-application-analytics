"""Schema definitions and column mappings for application analytics."""

from __future__ import annotations

import re
from typing import Dict, List

EXPECTED_COLUMNS: List[str] = [
    "bewerbungsdatum",
    "unternehmen",
    "position",
    "status",
    "quelle",
    "arbeitsmodell",
    "letzter_kontakt",
    "rueckmeldung_bis",
    "wartezeit_tage",
    "ranking_score",
]

DATE_COLUMNS: List[str] = ["bewerbungsdatum", "letzter_kontakt", "rueckmeldung_bis"]
NUMERIC_COLUMNS: List[str] = ["wartezeit_tage", "ranking_score"]

# Keys are expected in normalized form (same rules as normalize_column_name).
SYNONYM_MAPPING: Dict[str, str] = {
    "bewerbungsdatum": "bewerbungsdatum",
    "datum": "bewerbungsdatum",
    "date": "bewerbungsdatum",
    "unternehmen": "unternehmen",
    "firma": "unternehmen",
    "arbeitgeber": "unternehmen",
    "position": "position",
    "rolle": "position",
    "jobtitel": "position",
    "status": "status",
    "bewerbungsstatus": "status",
    "quelle": "quelle",
    "kanal": "quelle",
    "source": "quelle",
    "plattform": "quelle",
    "arbeitsmodell": "arbeitsmodell",
    "work_model": "arbeitsmodell",
    "arbeitsweise": "arbeitsmodell",
    "arbeitsort": "arbeitsmodell",
    "letzter_kontakt": "letzter_kontakt",
    "last_contact": "letzter_kontakt",
    "rueckmeldung_bis": "rueckmeldung_bis",
    "feedback_bis": "rueckmeldung_bis",
    "wartezeit_tage": "wartezeit_tage",
    "wartezeit_tagen": "wartezeit_tage",
    "wartezeit": "wartezeit_tage",
    "wartezeit_tag": "wartezeit_tage",
    "wartezeit_tage_": "wartezeit_tage",
    "ranking_score": "ranking_score",
    "ranking": "ranking_score",
    "score": "ranking_score",
}


def normalize_column_name(value: str) -> str:
    """Normalize a raw column name to a stable machine-friendly format."""
    text = str(value).strip().lower()
    text = (
        text.replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ü", "ue")
        .replace("ß", "ss")
    )
    text = text.replace(" ", "_")
    text = re.sub(r"[^a-z0-9_]", "", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text
