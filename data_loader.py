"""
Modul zum Einlesen aller Dateien für das Cross-Selling Zuordnungs-Tool.
"""

import pandas as pd
from pathlib import Path
from typing import Dict, Optional, Tuple
import os


DATA_DIR = Path(__file__).parent / "data"
UPLOADS_DIR = Path(__file__).parent / "uploads"
OUTPUTS_DIR = Path(__file__).parent / "outputs"

ZUBEHOER_FILE = DATA_DIR / "zubehoer.csv"
KRITERIEN_FILE = DATA_DIR / "crossselling-kriterien.xlsx"


def ensure_directories():
    """Erstellt alle benötigten Verzeichnisse falls nicht vorhanden."""
    DATA_DIR.mkdir(exist_ok=True)
    UPLOADS_DIR.mkdir(exist_ok=True)
    OUTPUTS_DIR.mkdir(exist_ok=True)


def load_zubehoer() -> Tuple[Optional[pd.DataFrame], str]:
    """
    Lädt die Zubehör-Datenbank.
    
    Returns:
        Tuple aus DataFrame und Status-Nachricht
    """
    if not ZUBEHOER_FILE.exists():
        return None, "zubehoer.csv nicht gefunden. Bitte Datei hochladen."
    
    try:
        df = pd.read_csv(ZUBEHOER_FILE, sep=';', encoding='utf-8')
        
        # Nur aktive Artikel behalten (isActive == True/1/"TRUE"/"1")
        if 'isActive' in df.columns:
            df['isActive'] = df['isActive'].astype(str).str.lower()
            df = df[df['isActive'].isin(['true', '1', 'yes', 'ja'])]
        
        # Spaltennamen normalisieren
        df.columns = df.columns.str.lower().str.strip()
        
        mod_time = os.path.getmtime(ZUBEHOER_FILE)
        from datetime import datetime
        mod_date = datetime.fromtimestamp(mod_time).strftime("%d.%m.%Y %H:%M")
        
        return df, f"✅ Geladen: {len(df)} aktive Artikel | Zuletzt geändert: {mod_date}"
    
    except Exception as e:
        return None, f"❌ Fehler beim Laden: {str(e)}"


def load_kriterien() -> Tuple[Optional[Dict], str]:
    """
    Lädt die Kriterien-Datei und extrahiert die Regeln pro Kategorie.
    
    Returns:
        Tuple aus Kriterien-Dict und Status-Nachricht
    """
    if not KRITERIEN_FILE.exists():
        return None, "crossselling-kriterien.xlsx nicht gefunden."
    
    try:
        df = pd.read_excel(KRITERIEN_FILE)
        
        # Kriterien parsen - die Struktur basiert auf dem gelesenen Format
        kriterien = {}
        
        # Finde Zeilen mit Kategorien (Spalte "Hauptkategorie" oder erste Spalte)
        df.columns = [str(c).strip() for c in df.columns]
        
        # Suche nach Kategorie-Spalte
        kategorie_col = None
        produktkat_col = None
        
        for col in df.columns:
            col_lower = col.lower()
            if 'hauptkategorie' in col_lower:
                kategorie_col = col
            if 'produktkategorie' in col_lower:
                produktkat_col = col
        
        if produktkat_col is None:
            produktkat_col = df.columns[1] if len(df.columns) > 1 else df.columns[0]
        
        # Parse jede Zeile als Kategorie-Regel
        for idx, row in df.iterrows():
            if idx < 2:  # Header-Zeilen überspringen
                continue
                
            produktkat = str(row.get(produktkat_col, '')).lower().strip()
            
            if pd.isna(produktkat) or produktkat == 'nan' or produktkat == '':
                continue
            
            # Kategorienamen normalisieren
            kat_key = normalize_kategorie(produktkat)
            
            if kat_key:
                kriterien[kat_key] = {
                    'original_name': produktkat,
                    'prio1': extract_prio_info(row, 'prio 1', df.columns),
                    'prio2': extract_prio_info(row, 'prio 2', df.columns),
                    'prio3': extract_prio_info(row, 'prio 3', df.columns),
                    'prio4': extract_prio_info(row, 'prio 4', df.columns),
                }
        
        return kriterien, f"✅ {len(kriterien)} Kategorie-Regeln geladen"
    
    except Exception as e:
        return None, f"❌ Fehler beim Laden der Kriterien: {str(e)}"


def normalize_kategorie(kat: str) -> Optional[str]:
    """Normalisiert Kategorie-Namen für einheitliches Matching."""
    kat = kat.lower().strip()
    
    mappings = {
        'kaminofen': ['kaminöfen', 'kaminofen', 'holzöfen', 'holzofen'],
        'pelletofen': ['pelletöfen', 'pelletofen'],
        'kamineinsatz': ['kamineinsätze', 'kamineinsatz'],
        'systemkamin': ['systemkamine', 'systemkamin'],
        'küchenofen': ['küchenöfen', 'küchenofen', 'kuechenofen'],
        'wasserfuehrend_set': ['wasserführende kamine/herde im set', 'wasserführend set'],
        'wasserfuehrend_einzeln': ['wasserführende kamine einzeln', 'wasserführend einzeln'],
        'grill': ['grills', 'grill'],
    }
    
    for key, variants in mappings.items():
        for variant in variants:
            if variant in kat:
                return key
    
    # Falls keine Zuordnung, original zurückgeben (bereinigt)
    return kat.replace(' ', '_').replace('ö', 'oe').replace('ü', 'ue').replace('ä', 'ae')


def extract_prio_info(row, prio_marker: str, columns) -> Dict:
    """Extrahiert Informationen für eine Prioritätsstufe."""
    info = {'produkt': None, 'kriterien': []}
    
    for col in columns:
        col_lower = str(col).lower()
        if prio_marker in col_lower:
            val = row.get(col, '')
            if pd.notna(val) and str(val).strip():
                val_str = str(val).strip()
                if 'produkt' in col_lower:
                    info['produkt'] = val_str
                elif 'kriterium' in col_lower or 'kriterien' in col_lower:
                    info['kriterien'].append(val_str)
                else:
                    # Erstes Vorkommen = Produkt, weitere = Kriterien
                    if info['produkt'] is None:
                        info['produkt'] = val_str
                    else:
                        info['kriterien'].append(val_str)
    
    return info


def load_produkte(file_path: str) -> Tuple[Optional[pd.DataFrame], str]:
    """
    Lädt die vom Nutzer hochgeladene Produktliste.
    
    Args:
        file_path: Pfad zur hochgeladenen Excel-Datei
    
    Returns:
        Tuple aus DataFrame und Status-Nachricht
    """
    try:
        df = pd.read_excel(file_path)
        
        # Spaltennamen normalisieren
        df.columns = df.columns.str.lower().str.strip()
        
        return df, f"✅ {len(df)} Produkte geladen"
    
    except Exception as e:
        return None, f"❌ Fehler beim Laden: {str(e)}"


def save_zubehoer(file_path: str) -> Tuple[bool, str]:
    """
    Ersetzt die Zubehör-Datenbank mit einer neuen Datei.
    
    Args:
        file_path: Pfad zur neuen Zubehör-Datei
    
    Returns:
        Tuple aus Erfolg und Status-Nachricht
    """
    try:
        import shutil
        ensure_directories()
        shutil.copy(file_path, ZUBEHOER_FILE)
        return True, "✅ zubehoer.csv erfolgreich ersetzt"
    except Exception as e:
        return False, f"❌ Fehler: {str(e)}"
