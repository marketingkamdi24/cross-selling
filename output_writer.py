"""
Modul zum Schreiben der Ergebnis-Dateien.
"""

import pandas as pd
from pathlib import Path
from typing import Tuple
import os


def save_result(
    df: pd.DataFrame,
    original_filename: str,
    output_dir: Path
) -> Tuple[str, str]:
    """
    Speichert das Ergebnis als Excel-Datei.
    
    Args:
        df: DataFrame mit Ergebnissen
        original_filename: Ursprünglicher Dateiname
        output_dir: Ausgabeverzeichnis
    
    Returns:
        Tuple aus Dateipfad und Status-Nachricht
    """
    try:
        output_dir.mkdir(exist_ok=True)
        
        # Dateiname generieren
        base_name = Path(original_filename).stem
        output_filename = f"{base_name}_crossselling.xlsx"
        output_path = output_dir / output_filename
        
        # Falls Datei existiert, nummerieren
        counter = 1
        while output_path.exists():
            output_filename = f"{base_name}_crossselling_{counter}.xlsx"
            output_path = output_dir / output_filename
            counter += 1
        
        # Excel schreiben
        df.to_excel(output_path, index=False, engine='openpyxl')
        
        return str(output_path), f"✅ Gespeichert: {output_filename}"
    
    except Exception as e:
        return "", f"❌ Fehler beim Speichern: {str(e)}"


def format_preview_table(df: pd.DataFrame, max_rows: int = 20) -> pd.DataFrame:
    """
    Erstellt eine formatierte Vorschau-Tabelle.
    
    Args:
        df: DataFrame mit Ergebnissen
        max_rows: Maximale Anzahl anzuzeigender Zeilen
    
    Returns:
        Formatierter DataFrame für Anzeige
    """
    # Relevante Spalten für Vorschau auswählen
    preview_cols = []
    
    # Prioritäre Spalten
    priority_cols = ['produktname', 'name', 'hersteller', 'durchmesser', 'crossselling', 'crossselling_namen', 'cs_hinweis']
    
    for col in priority_cols:
        if col in df.columns:
            preview_cols.append(col)
    
    # Falls keine der Prioritätsspalten vorhanden, erste paar + CS-Spalten
    if not preview_cols:
        preview_cols = list(df.columns[:3])
        if 'crossselling' in df.columns:
            preview_cols.append('crossselling')
        if 'crossselling_namen' in df.columns:
            preview_cols.append('crossselling_namen')
    
    preview_df = df[preview_cols].head(max_rows).copy()
    
    # Lange Strings kürzen für bessere Darstellung
    for col in preview_df.columns:
        preview_df[col] = preview_df[col].astype(str).apply(
            lambda x: x[:100] + "..." if len(x) > 100 else x
        )
    
    return preview_df
