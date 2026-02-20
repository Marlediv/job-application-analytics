"""Ingestion and cleaning pipeline for job application analytics."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .schema import DATE_COLUMNS, EXPECTED_COLUMNS, NUMERIC_COLUMNS, SYNONYM_MAPPING, normalize_column_name


RAW_FILE = Path("data/raw/Bewerbungsliste.xlsx")
PROCESSED_FILE = Path("data/processed/applications.csv")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _read_first_sensible_sheet(excel_path: Path) -> pd.DataFrame:
    workbook = pd.ExcelFile(excel_path)

    for sheet_name in workbook.sheet_names:
        sheet_df = pd.read_excel(workbook, sheet_name=sheet_name)
        cleaned = sheet_df.dropna(how="all").dropna(axis=1, how="all")

        if cleaned.shape[0] >= 1 and cleaned.shape[1] >= 2:
            print(f"[INFO] Verwende Tabellenblatt: {sheet_name}")
            return cleaned.reset_index(drop=True)

    raise ValueError("Keine sinnvolle Tabelle gefunden: Alle Tabellenblaetter sind leer oder unbrauchbar.")


def _apply_column_mapping(df: pd.DataFrame) -> pd.DataFrame:
    rename_map: dict[str, str] = {}
    seen: dict[str, int] = {}

    for original in df.columns:
        normalized = normalize_column_name(original)
        canonical = SYNONYM_MAPPING.get(normalized, normalized)

        # Prevent duplicate column names after synonym mapping.
        if canonical in seen:
            seen[canonical] += 1
            target = f"{canonical}_{seen[canonical]}"
        else:
            seen[canonical] = 0
            target = canonical

        rename_map[original] = target

    return df.rename(columns=rename_map)


def _clean_strings(df: pd.DataFrame) -> pd.DataFrame:
    for column in df.select_dtypes(include=["object", "string"]).columns:
        df[column] = df[column].astype("string").str.strip()
        df[column] = df[column].replace("", pd.NA)
    return df


def _convert_dates(df: pd.DataFrame) -> pd.DataFrame:
    for col in DATE_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
    return df


def _convert_numeric(df: pd.DataFrame) -> pd.DataFrame:
    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            if df[col].dtype == "object" or str(df[col].dtype).startswith("string"):
                prepared = (
                    df[col]
                    .astype("string")
                    .str.replace(".", "", regex=False)
                    .str.replace(",", ".", regex=False)
                )
                df[col] = pd.to_numeric(prepared, errors="coerce")
            else:
                df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _warn_missing_expected_columns(df: pd.DataFrame) -> None:
    missing = [col for col in EXPECTED_COLUMNS if col not in df.columns]
    if missing:
        print("[WARN] Erwartete Spalten fehlen:", ", ".join(missing))


def _print_summary(df: pd.DataFrame) -> None:
    print("\n=== Ingestion Zusammenfassung ===")
    print(f"Rows: {df.shape[0]}")
    print(f"Cols: {df.shape[1]}")

    missing_top = df.isna().sum().sort_values(ascending=False).head(10)
    print("Missing Values Top 10:")
    for column, missing_count in missing_top.items():
        print(f"- {column}: {int(missing_count)}")


def run_ingestion(
    raw_file: Path | str = RAW_FILE,
    processed_file: Path | str = PROCESSED_FILE,
) -> pd.DataFrame:
    root = _repo_root()
    raw_path = root / Path(raw_file)
    processed_path = root / Path(processed_file)

    if not raw_path.exists():
        raise FileNotFoundError(
            "Excel-Datei nicht gefunden. Erwartet unter: "
            f"{raw_path}. Bitte lege 'Bewerbungsliste.xlsx' in 'data/raw/' ab."
        )

    df = _read_first_sensible_sheet(raw_path)
    df = _apply_column_mapping(df)
    df = _clean_strings(df)
    df = _convert_dates(df)
    df = _convert_numeric(df)

    _warn_missing_expected_columns(df)

    processed_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(processed_path, index=False, encoding="utf-8")
    print(f"[INFO] CSV geschrieben nach: {processed_path}")

    _print_summary(df)
    return df


def main() -> int:
    try:
        run_ingestion()
        return 0
    except FileNotFoundError as exc:
        print(f"[ERROR] {exc}")
        return 1
    except Exception as exc:  # pragma: no cover
        print(f"[ERROR] Ingestion fehlgeschlagen: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
