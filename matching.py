"""
Matching-Algorithmus für Cross-Selling Zuordnung.
"""

import pandas as pd
from typing import Dict, List, Tuple, Optional
import re
import random
from concurrent.futures import ProcessPoolExecutor, as_completed


# ========================================
# HAUPTPRODUKT-KATEGORIEN - Diese dürfen NIE als Cross-Selling zugeordnet werden!
# ========================================
HAUPTPRODUKT_TYPEN = {
    'kaminofen', 'kaminöfen', 'holzofen', 'pelletofen', 'pelletöfen',
    'kamineinsatz', 'kamineinsätze', 'kaminbausatz', 'gaseinsatz', 'gaskamin',
    'elektrokamin', 'küchenofen', 'küchenherd', 'holzherd', 'ethanolofen', 'ölofen',
    'pelleteinsatz', 'pelletkessel', 'kombi kamin',
    'gasgrill', 'holzkohlegrill', 'kugelgrill', 'kamadogrill', 'pelletgrill',
    'keramikgrill', 'grillwagen', 'grillstation', 'grillküche', 'campinggrill', 'tischgrill',
    'säulengrill', 'schwenkgrill', 'räucherofen', 'smoker', 'pizzaofen', 'feuerschale',
}

# ========================================
# ZUBEHÖR-KATEGORIEN für Diversität
# Pro Kategorie wird max. 1-2 Artikel ausgewählt
# ========================================
ZUBEHOER_KATEGORIEN = {
    'rohrelemente': ['längenelement', 'bogen', 'reduzierung', 'erweiterung', 't-stück', 'rohr'],
    'anschluss': ['anschlusskomponenten', 'wandfutter', 'wanddurchführung', 'dachdurchführung', 'adapter'],
    'abschluss': ['rosette', 'blindkappe', 'mündungsabschluss', 'regenhaube'],
    'reinigung': ['reinigungselement', 'aschesauger', 'kaminreiniger', 'reinigung', 'bürste'],
    'kamingarnitur': ['kamingarnitur', 'kaminbesteck', 'kaminset', 'kaminwerkzeug'],
    'kaminventilator': ['kaminventilator', 'ofenventilator', 'kamin ventilator', 'rauchgasventilator'],
    'vermiculite': ['vermiculite', 'vermiculiteplatte', 'feuerraumauskleidung'],
    'brennstoff': ['anzündhilfe', 'anzündwolle', 'anzünder', 'brennstoff', 'holzbrikett', 'kaminholz', 'brennholz'],
    'funkenschutz': ['funkenschutz', 'bodenplatte', 'grundplatte', 'glasplatte'],
    'befestigung': ['rohrschelle', 'befestigung', 'konsole', 'montagezubehör', 'dachhaken'],
    'abdeckung': ['abdeckung', 'abdeckhaube', 'thermoschild', 'blende'],
    'schornstein': ['schornstein-zubehör', 'schornstein'],
    'sonstiges': ['sonstige', 'set', 'zubehör'],
}

# ========================================
# KATEGORIE-TRENNUNG: Welches Zubehör gehört zu welcher Hauptkategorie?
# Ein Kaminofen darf NUR Kaminofen-Zubehör bekommen, KEINE Grillprodukte!
# ========================================
KAMINOFEN_ZUBEHOER_KATEGORIEN = {
    'anschlusskomponenten', 'kaminverkleidung', 'kaminbauplatten', 'rauchrohre',
    'ofenrohre', 'rauchrohrset', 'wandfutter', 'rosetten', 'reinigung',
    'aschesauger', 'kamingarnitur', 'funkenschutz', 'bodenplatte', 'glasplatte',
    'kaminventilator', 'vermiculite', 'dichtung', 'feuerraumauskleidung',
    'abbrandsteuerung', 'schornstein', 'rauchwarnmelder', 'kohlenmonoxidwarner',
    'anzündhilfen', 'anzündwolle', 'kaminbesteck', 'holzkorb', 'holzlege',
    'ofenhandschuh', 'aschekasten', 'luftgitter', 'montagerahmen', 'blenden',
}

GRILL_ZUBEHOER_KATEGORIEN = {
    'abdeckhaube', 'grillabdeckung', 'grillpfannen', 'grillbesteck', 'grillzange',
    'fleischthermometer', 'grillthermometer', 'räucherchips', 'räucherspäne',
    'räuchermehl', 'räucherpellets', 'räucherholz', 'grillplanken', 'grillpapier',
    'holzkohle', 'briketts', 'anzünder', 'grillanzünder', 'grillschürze',
    'grillbürste', 'grillreiniger', 'grillrost', 'pizzastein', 'pizzaschieber',
    'pizzaschaufel', 'pizzazubehör', 'dutch oven', 'gusseisen', 'wok',
    'grillkochbuch', 'rubs', 'marinaden', 'gewürzmischungen', 'saucen',
    'seitenbrenner', 'drehspieß', 'hähnchenbräter', 'spareribs halter',
}

PELLET_ZUBEHOER_KATEGORIEN = {
    'pelletrohre', 'ofenanschlussstück', 'pelletlager', 'pelletsilos',
    'pelletbehälter', 'pellets', 'pelletsackware', 'wifi-modul', 'fernbedienung',
    'funkenschutz', 'bodenplatte', 'glasplatte', 'reinigung', 'aschesauger',
}

SAUNA_ZUBEHOER_KATEGORIEN = {
    'saunasteine', 'aufguss', 'saunaeimer', 'saunakelle', 'sanduhr',
    'thermometer', 'hygrometer', 'saunasteuerung', 'wärmeplatte',
}

HEIZTECHNIK_ZUBEHOER_KATEGORIEN = {
    'rücklaufanhebung', 'thermische ablaufsicherung', 'sicherheitsventil',
    'heizungssteuerung', 'pufferspeicher', 'ausdehnungsgefäß', 'tauchhülsen',
    'speicherthermometer', 'kugelhahn', 'entlüfter', 'brauchwassermischer',
    'heizkreisverteiler', 'pumpengruppe', 'mischer', 'stellmotor',
}

# ========================================
# MARKEN-TRENNUNG: Diese Kamin-Hersteller gehören NUR zum Kaminbereich!
# Dürfen NIEMALS bei Grillprodukten als Crossselling erscheinen!
# ========================================
KAMIN_ONLY_MARKEN = {
    'raik', 'opsinox', 'la nordica', 'holetherm',
    'schiedel', 'schindler + hofmann', 'schindler+hofmann',
    'brula', 'promat',
}

# GRILL-ONLY-MARKEN: Diese Hersteller gehören NUR zum Grillbereich!
# Dürfen NIEMALS bei Kaminprodukten als Crossselling erscheinen!
GRILL_ONLY_MARKEN = {
    'weber', 'big green egg', 'kamado joe', 'traeger', 'masterbuilt',
    'napoleon', 'outdoorchef', 'char-griller', 'campingaz', 'cadac',
    'everdure', 'ooni', 'gozney', 'moesta', 'monolith', 'the bastard',
    'grill guru', 'yakiniku', 'primo', 'grandhall', 'beefer',
    'arteflame', 'cobb', 'solo stove', 'ofyr', 'thüros', 'thueros',
    'enders', 'justus grill', 'camp chef', 'alfa forni', 'asteus',
    'hot wok', 'otto wilde', 'fire magic', 'grillson', 'witt',
    'mr. barrel bbq', 'don marco\'s barbecue', "don marco's barbecue",
    'rock\'n\'rubs', "rock'n'rubs", 'ankerkraut', 'axtschlag',
    'sausguru', 'saus.guru', 'der merklinger', 'feuergott',
    'meater', 'the meatstick', 'grill-id', 'höfats', 'hoefats',
    'feuerhand', 'petromax', 'heatstrip',
}

# HEIZUNG/SOLAR-MARKEN: Dürfen NIEMALS als CS bei Kamin oder Grill erscheinen!
HEIZUNG_SOLAR_MARKEN = {
    'sunex', 'westech solar', 'westech', 'austroflex', 'daikin',
    'atmos', 'watts industries', 'afriso', 'termoventiler', 'esbe',
    'resol', 'regulus', 'lk armatur', 'lk armatur deutschland gmbh',
    'sorel', 'ja solar', 'hoymiles', 'huawei', 'yuma', 'jackery',
    'ensol', 'linuo solar',
}

# ERLAUBTE PRODUKTNAMEN für Kamin-Hersteller (Raik, Opsinox, La Nordica, Holetherm)
# Diese Hersteller dürfen NUR zugeordnet werden, wenn einer dieser Begriffe im Produktnamen steht!
RAIK_OPSINOX_ERLAUBTE_PRODUKTNAMEN = {
    'kaminofen', 'pelletofen', 'werkstattofen', 'kamin', 
    'pelletkessel', 'küchenofen', 'kuechenofen', 'kamineinsatz'
}

# ========================================
# BEKANNTE MODELLNAMEN für Modell-Matching
# Wenn ein Produkt ein spezifisches Modell im Namen hat, dürfen CS-Artikel
# mit einem ANDEREN Modell NICHT zugeordnet werden!
# CS-Artikel OHNE Modellname (generisches Zubehör) sind weiterhin erlaubt.
# ========================================
BEKANNTE_MODELLE = {
    # Weber Modelle
    'genesis', 'spirit', 'summit', 'lumin', 'smokefire', 'master-touch',
    'master touch', 'performer', 'original kettle', 'go-anywhere',
    'traveler', 'pulse', 'q 1200', 'q 2200', 'q 3200',
    # Höfats Modelle
    'moon 45', 'moon', 'cube', 'ellipse', 'bowl', 'spin', 'cone', 'beer box',
    # Napoleon Modelle
    'rogue', 'prestige', 'phantom', 'freestyle',
    # Kamado Joe Modelle
    'classic joe', 'big joe', 'joe jr',
    # Traeger Modelle
    'ironwood', 'timberline', 'pro series',
    # Outdoorchef Modelle
    'ascona', 'davos', 'lugano', 'arosa', 'chelsea',
    # Ooni Modelle
    'koda', 'fyra', 'karu', 'volt',
    # Monolith Modelle
    'le chef',
    # Enders Modelle
    'boston', 'monroe', 'kansas', 'chicago',
    # Kamin-Modelle (Extraflame, La Nordica etc.)
    'amika evo', 'amika', 'giusy evo', 'giusy', 'ketty evo', 'ketty',
    'rosy', 'dahiana', 'tosca plus', 'melinda idro', 'melinda',
    'rossella plus', 'dorella', 'irina',
    # Weitere Kamin-Modelle
    'polar neo', 'color flex',
}

# Big Green Egg Größen/Modelle - NUR bei BGE-Artikeln als Modell erkennen!
# Diese Begriffe sind zu generisch (xl, large, small, medium, mini) und würden
# sonst auch bei Nicht-BGE-Artikeln matchen (z.B. "Gozney Dome XL")
BGE_GROESSEN_MODELLE = {
    'minimax', 'xlarge', '2xlarge', 'xxlarge', '2xl', 'xxl',
    'xl', 'large', 'medium', 'small', 'mini',
}

# BGE Größen-Normalisierung: Verschiedene Schreibweisen → einheitliche Form
# z.B. '2xl', 'xxl', 'xxlarge' → alle zu '2xlarge'
BGE_GROESSEN_NORMALISIERUNG = {
    'xl': 'xlarge',
    '2xl': '2xlarge',
    'xxl': '2xlarge',
    'xxlarge': '2xlarge',
}

# ========================================
# EXTRAFLAME PELLETOFEN: WiFi-Modul + Fernbedienung als Pflichtartikel
# Total Control 1.0 = ältere Modelle, Total Control 3.0 = 2022+ Modelle
# ========================================

# Extraflame Modelle die Total Control 3.0 verwenden (2022+ Generation)
# Quelle: https://www.lanordica-extraflame.com/de/losungen/uberwachen-sie-ihren-ofen-mit-der-app-total-control
EXTRAFLAME_TC3_MODELLE = {
    'mirka', 'noris', 'marina idro', 'comfort p70',
    'katia', 'ilary', 'angy', 'mariella',
}

# WiFi-Modul Artikel-IDs + Artikelnummern (beides nötig für Deduplizierung)
EXTRAFLAME_WIFI_TC1_ID = '19341'       # WIFI-Modul 2019 Weiß für Total Control 1.0
EXTRAFLAME_WIFI_TC1_ARTNR = '9278442'  # Artikelnummer in zubehoer.csv
EXTRAFLAME_WIFI_TC3_ID = '19343'       # WiFi-Modul 2022 Grau für Total Control 3.0
EXTRAFLAME_WIFI_TC3_ARTNR = '9278512'  # Artikelnummer in zubehoer.csv

# Fernbedienung Artikel-IDs + Artikelnummern
EXTRAFLAME_FB_A_ID = '19572'           # Fernbedienung Version A (für TC 1.0)
EXTRAFLAME_FB_A_ARTNR = 'X2272590'    # Artikelnummer
EXTRAFLAME_FB_B_ID = '19573'           # Fernbedienung Version B (für TC 3.0)
EXTRAFLAME_FB_B_ARTNR = 'X2272591'    # Artikelnummer
EXTRAFLAME_FB_DISPLAY_ID = '19576'     # Fernbedienung mit grafischem Display
EXTRAFLAME_FB_DISPLAY_ARTNR = 'X9278281'  # Artikelnummer

# Alle Extraflame WiFi/FB Artikel-IDs und Artikelnummern (für Deduplizierung)
EXTRAFLAME_WIFI_FB_ALL_IDS = {
    EXTRAFLAME_WIFI_TC1_ID, EXTRAFLAME_WIFI_TC1_ARTNR,
    EXTRAFLAME_WIFI_TC3_ID, EXTRAFLAME_WIFI_TC3_ARTNR,
    EXTRAFLAME_FB_A_ID, EXTRAFLAME_FB_A_ARTNR,
    EXTRAFLAME_FB_B_ID, EXTRAFLAME_FB_B_ARTNR,
    EXTRAFLAME_FB_DISPLAY_ID, EXTRAFLAME_FB_DISPLAY_ARTNR,
}


def is_extraflame_pelletofen(produkt_kategorie: Optional[str], produkt_name: Optional[str], produkt_hersteller: Optional[str]) -> bool:
    """Prüft ob ein Produkt ein Extraflame Pelletofen ist."""
    name_lower = (produkt_name or '').lower()
    hersteller_lower = (produkt_hersteller or '').lower()
    kat_lower = (produkt_kategorie or '').lower()
    
    is_extraflame = 'extraflame' in hersteller_lower or 'extraflame' in name_lower
    is_pellet = 'pellet' in kat_lower or 'pelletofen' in name_lower or 'pelletkessel' in name_lower
    
    return is_extraflame and is_pellet


def get_extraflame_tc_version(produkt_name: Optional[str]) -> int:
    """
    Bestimmt die Total Control Version eines Extraflame Pelletofens.
    
    TC 3.0 Modelle (2022+): Mirka, Noris, Marina Idro, Comfort P70, Katia, Ilary, Angy, Mariella
    TC 1.0: Alle anderen (ältere Modelle wie Souvenir, Ketty, Giusy, Annabella, Serafina etc.)
    
    Returns: 3 für TC 3.0, 1 für TC 1.0
    """
    name_lower = (produkt_name or '').lower()
    
    for modell in EXTRAFLAME_TC3_MODELLE:
        if modell in name_lower:
            return 3
    
    return 1


def find_extraflame_wifi_fernbedienung(produkt_kategorie: Optional[str], produkt_name: Optional[str], produkt_hersteller: Optional[str]) -> Tuple[Optional[Dict], Optional[Dict]]:
    """
    Findet passendes WiFi-Modul und Fernbedienung für Extraflame Pelletöfen.
    
    Zuordnung:
    - TC 1.0 → WiFi-Modul 2019 Weiß (19341) + Fernbedienung Version A (19572)
    - TC 3.0 → WiFi-Modul 2022 Grau (19343) + Fernbedienung Version B (19573)
    
    Returns: (wifi_artikel, fernbedienung_artikel) oder (None, None)
    """
    if not is_extraflame_pelletofen(produkt_kategorie, produkt_name, produkt_hersteller):
        return None, None
    
    tc_version = get_extraflame_tc_version(produkt_name)
    
    if tc_version == 3:
        wifi = {
            'artikel_id': EXTRAFLAME_WIFI_TC3_ID,
            'name': 'Extraflame WiFi-Modul 2022 Grau für Total Control 3.0',
            'score': 998,
            'hersteller': 'Extraflame',
            'farbe': '',
            'zubehoer_kategorie': 'extraflame_wifi',
            'gleicher_hersteller': True,
        }
        fernbedienung = {
            'artikel_id': EXTRAFLAME_FB_B_ID,
            'name': 'Fernbedienung Extraflame Version B',
            'score': 997,
            'hersteller': 'Extraflame',
            'farbe': '',
            'zubehoer_kategorie': 'extraflame_fernbedienung',
            'gleicher_hersteller': True,
        }
    else:
        wifi = {
            'artikel_id': EXTRAFLAME_WIFI_TC1_ID,
            'name': 'Extraflame WIFI-Modul 2019 Weiß für Total Control 1.0',
            'score': 998,
            'hersteller': 'Extraflame',
            'farbe': '',
            'zubehoer_kategorie': 'extraflame_wifi',
            'gleicher_hersteller': True,
        }
        fernbedienung = {
            'artikel_id': EXTRAFLAME_FB_A_ID,
            'name': 'Fernbedienung Extraflame Version A',
            'score': 997,
            'hersteller': 'Extraflame',
            'farbe': '',
            'zubehoer_kategorie': 'extraflame_fernbedienung',
            'gleicher_hersteller': True,
        }
    
    return wifi, fernbedienung


def normalize_modell(modell: str) -> str:
    """Normalisiert Modellnamen (z.B. BGE Größen: '2xl' → '2xlarge')."""
    return BGE_GROESSEN_NORMALISIERUNG.get(modell, modell)


def _is_bge_name(name_lower: str) -> bool:
    """Prüft ob ein Produktname ein Big Green Egg Artikel ist.
    Erkennt auch Varianten wie 'Big Green XLarge Egg' wo die Größe zwischen Green und Egg steht."""
    if 'big green egg' in name_lower or 'bge' in name_lower:
        return True
    if 'big green' in name_lower and 'egg' in name_lower:
        return True
    return False


def extract_all_modelle_from_name(name: str, hersteller: Optional[str] = None) -> set:
    """
    Extrahiert ALLE bekannten Modellnamen aus einem Produktnamen (normalisiert).
    Wichtig für CS-Artikel die mehrere Größen nennen, z.B.
    "Big Green Egg Ascheschieber für XLarge und 2XLarge" → {'xlarge', '2xlarge'}
    
    BGE-Größen (xl, large, medium etc.) werden NUR bei BGE-Artikeln erkannt,
    da diese Begriffe zu generisch sind für andere Hersteller.
    """
    if not name:
        return set()
    
    name_lower = name.lower().strip()
    found = set()
    is_bge = _is_bge_name(name_lower) or (hersteller and _is_bge_name(hersteller.lower()))
    
    # Allgemeine Modelle prüfen (längste zuerst)
    sorted_modelle = sorted(BEKANNTE_MODELLE, key=len, reverse=True)
    for modell in sorted_modelle:
        pattern = r'\b' + re.escape(modell) + r'\b'
        if re.search(pattern, name_lower):
            found.add(normalize_modell(modell))
    
    # BGE-Größen NUR bei BGE-Artikeln prüfen
    if is_bge:
        sorted_bge = sorted(BGE_GROESSEN_MODELLE, key=len, reverse=True)
        for modell in sorted_bge:
            pattern = r'\b' + re.escape(modell) + r'\b'
            if re.search(pattern, name_lower):
                found.add(normalize_modell(modell))
    
    return found


def extract_modell_from_name(name: str, hersteller: Optional[str] = None) -> Optional[str]:
    """
    Extrahiert den Modellnamen aus einem Produktnamen.
    
    NUR bekannte Modelle aus BEKANNTE_MODELLE werden erkannt!
    BGE-Größen werden NUR bei BGE-Artikeln erkannt.
    Verwendet WORTGRENZEN-Matching, damit z.B. 'lumin' NICHT in 'Aluminium' gefunden wird.
    
    Beispiele:
    - "höfats MOON 45 Feuerschale" → "moon 45"
    - "Weber Genesis Gasgrill" → "genesis"
    - "Extraflame Amika EVO Kaminofen" → "amika evo"
    - "Weber Grillzange" → None (kein Modell, generisches Zubehör)
    - "Thüros Grillreinigungsblock" → None (kein bekanntes Modell)
    - "Aluminium Dutch Oven" → None (NICHT 'lumin'!)
    - "Gozney Dome XL" → None (XL ist BGE-Größe, kein allgemeines Modell)
    """
    if not name:
        return None
    
    name_lower = name.lower().strip()
    is_bge = _is_bge_name(name_lower) or (hersteller and _is_bge_name(hersteller.lower()))
    
    # Prüfe bekannte Modelle (längste zuerst, um "moon 45" vor "moon" zu finden)
    # WICHTIG: Wortgrenzen (\b) verwenden, damit 'lumin' nicht in 'aluminium' matched!
    sorted_modelle = sorted(BEKANNTE_MODELLE, key=len, reverse=True)
    for modell in sorted_modelle:
        pattern = r'\b' + re.escape(modell) + r'\b'
        if re.search(pattern, name_lower):
            return modell
    
    # BGE-Größen NUR bei BGE-Artikeln
    if is_bge:
        sorted_bge = sorted(BGE_GROESSEN_MODELLE, key=len, reverse=True)
        for modell in sorted_bge:
            pattern = r'\b' + re.escape(modell) + r'\b'
            if re.search(pattern, name_lower):
                return modell
    
    return None

# AUSSCHLUSS-KEYWORDS: Diese Artikel dürfen NIE als Cross-Selling zugeordnet werden
# (unabhängig von der Produktkategorie)
GLOBAL_AUSSCHLUSS_KEYWORDS = {
    # Heizungstechnik - nicht für Kaminöfen/Pelletöfen
    'solarwellrohr', 'solarspeicher', 'solarkollektor', 'solarstation',
    'heizkreisverteiler', 'pumpengruppe', 'stellmotor', 'mischer dn',
    '3-wege-mischer', '4-wege-mischer', '3-wege-zonenventil', 'zonenventil',
    '3-wege-verteilventil', 'verteilventil', 'thermostatkopf',
    'rücklaufanhebung', 'laddomat', 'thermovar', 'atmos ',
    'ausdehnungsgefäß', 'membran-ausdehnungsgefäß', 'sicherheitsventil',
    'brauchwassermischer', 'pufferspeicher', 'schichtenspeicher',
    'tauchhülse', 'speicherthermometer', 'kugelhahn', 'lk armatur',
    # Kessel-spezifisch
    'holzvergaser', 'pelletkessel', 'kombikessel', 'hackschnitzel',
    'pelletbehälter 1000', 'pelletsilos', 'förderschnecke',
    # Solar
    'austroflex', 'flexrohr dn',
    # Sonstige Heizungstechnik
    'sanierungsschornstein',
    'resol', 'vbus', 'schnittstellenadapter', 'regelung ',
    'regulus', 'filtermagnet', 'gaskessel', 'ölkessel',
    'afriso', 'gehäusethermostat', 'kapillarleitung', 'temperaturregler',
    'heizungspumpe', 'zirkulationspumpe', 'umwälzpumpe',
    # Solar/Photovoltaik - nie als CS
    'flachkollektor', 'solarkollektor', 'solarspeicher', 'solarstation',
    'solarwellrohr', 'solarthermie', 'photovoltaik', 'wechselrichter',
    'schrägdacherweiterungsset', 'schraegdacherweiterungsset',
    'flachdachmontageset', 'aufdachmontageset',
    # Outdoor/Camping - nicht für Kaminöfen
    'petroleumleuchte', 'petroleumlampe',
}

# ========================================
# KRITERIEN PRO PRODUKTKATEGORIE (aus WORKFLOW.md)
# Definiert welche Zubehör-Kategorien pro Produkttyp relevant sind
# ========================================
# Kaminofen-Kriterien (gilt auch für Werkstattofen, Küchenofen)
_KAMINOFEN_PRIOS = [
    ('reinigung', 1),          # PFLICHT: Aschesauger/Kaminreiniger
    ('kamingarnitur', 1),      # PFLICHT: Kaminbesteck/Kamingarnitur
    ('kaminventilator', 1),    # PFLICHT: Kaminventilator
    ('rohrelemente', 2),       # Rauchrohrset
    ('abschluss', 1),          # Rosette
    ('funkenschutz', 1),       # Funkenschutzplatte
    ('vermiculite', 1),        # Vermiculiteplatten
    ('brennstoff', 1),         # Kamin Brennstoff/Anzündhilfen
]

KATEGORIE_ZUBEHOER_PRIOS = {
    'pelletofen': [
        ('reinigung', 1),          # PFLICHT: Aschesauger/Kaminreiniger
        ('kamingarnitur', 1),      # PFLICHT: Kaminbesteck
        ('kaminventilator', 1),    # PFLICHT: Kaminventilator
        ('anschluss', 1),          # Ofenanschlussstück
        ('rohrelemente', 2),       # Rohrmaterialien
        ('abschluss', 1),          # Rosette
        ('funkenschutz', 1),       # Funkenschutzplatte
        ('schornstein', 1),        # Schornstein-Set
    ],
    'kaminofen': _KAMINOFEN_PRIOS,
    'werkstattofen': _KAMINOFEN_PRIOS,  # Wie Kaminofen
    'küchenofen': _KAMINOFEN_PRIOS,     # Wie Kaminofen
    'kuechenofen': _KAMINOFEN_PRIOS,    # Wie Kaminofen
    'holzofen': _KAMINOFEN_PRIOS,       # Wie Kaminofen
    'kamineinsatz': [
        ('reinigung', 1),          # PFLICHT: Aschesauger/Kaminreiniger
        ('kamingarnitur', 1),      # PFLICHT: Kaminbesteck/Kamingarnitur
        ('kaminventilator', 1),    # PFLICHT: Kaminventilator
        ('rohrelemente', 2),       # Rauchrohrset
        ('abschluss', 1),          # Rosette
        ('anschluss', 1),          # Montagerahmen/Blenden
        ('sonstiges', 1),          # Luftgitter etc.
    ],
    'grill': [
        ('abdeckung', 1),      # Prio 1: Abdeckhaube
        ('sonstiges', 2),      # Prio 2-3: Zubehör, Thermometer
        ('reinigung', 1),      # Prio 4: Reiniger
    ],
}


def detect_bereich_from_name(name: str, hersteller: Optional[str] = None) -> str:
    """
    Erkennt den Produktbereich PRIMÄR aus dem Produktnamen.
    Der Produktname enthält: Hersteller, Produkttyp, Spezifikationen.
    
    Returns: 'kamin', 'grill', 'heizung', 'sauna' oder 'unbekannt'
    """
    name_lower = (name or '').lower()
    hersteller_lower = (hersteller or '').lower()
    combined = name_lower + ' ' + hersteller_lower
    
    # 1. HERSTELLER-basierte Erkennung (aus Produktname oder Hersteller-Feld)
    # Heizung/Solar hat HÖCHSTE Priorität beim Ausschluss
    for marke in HEIZUNG_SOLAR_MARKEN:
        if marke in combined:
            return 'heizung'
    
    # Kamin-only Hersteller im Namen?
    for marke in KAMIN_ONLY_MARKEN:
        if marke in combined:
            return 'kamin'
    
    # Grill-only Hersteller im Namen?
    for marke in GRILL_ONLY_MARKEN:
        if marke in combined:
            return 'grill'
    
    # 2. PRODUKTTYP-Keywords im Namen
    kamin_typ_keywords = [
        'kaminofen', 'kaminoefen', 'holzofen', 'kamineinsatz', 'küchenofen',
        'kuechenofen', 'werkstattofen', 'systemkamin', 'pelletofen', 'pelletkessel',
        'rauchrohr', 'ofenrohr', 'kaminrohr', 'pelletrohr', 'abgasrohr',
        'längenelement', 'laengenelement', 'rohrelement', 'rohrset',
        'wandfutter', 'wanddurchführung', 'dachdurchführung',
        'rosette', 'mündungsabschluss', 'regenhaube', 'blindkappe',
        'glasplatte', 'glas-vorlegeplatte', 'vorlegeplatte', 'unterlegplatte',
        'funkenschutz', 'funkenschutzplatte',
        'kamingarnitur', 'aschesauger', 'kaminventilator', 'vermiculite',
        'feuerraum', 'abbrandsteuerung', 'schornstein', 'edelstahlschornstein',
        'rauchwarnmelder', 'kohlenmonoxid', 'co-melder',
        'kaminbesteck', 'holzkorb', 'holzlege', 'aschekasten', 'aschebox',
        'kaminbau', 'montagerahmen', 'kaminverkleidung',
        'kaminbauplatten', 'promasil', 'brula', 'luftgitter',
        'color flex', 'polar neo',
        # Schornstein-spezifisch
        'grundplatte', 'regenkragen', 'reduzierung ppl', 'erweiterung ics',
        'abdeckblende', 'wandkonsole', 'wandhalter', 'wakaflex',
        'doppelwandig', 'einwandig',
    ]
    
    grill_typ_keywords = [
        'grill', 'bbq', 'smoker', 'pizzaofen', 'kamado',
        'abdeckhaube', 'grillrost', 'grillbesteck', 'grillzange',
        'räucherchips', 'räucherspäne', 'räucherpellets', 'grillplanken',
        'grillbürste', 'grillreiniger', 'pizzastein', 'pizzaschieber',
        'dutch oven', 'drehspieß', 'spareribs', 'hähnchenbräter',
        'grillthermometer', 'fleischthermometer', 'grillhandschuh',
        'grillschürze', 'anzündkamin',
        'holzkohle', 'briketts', 'grillanzünder',
        'marinaden', 'rubs', 'gewürzmischung', 'saucen',
    ]
    
    sauna_keywords = ['sauna', 'aufguss', 'saunaeimer', 'saunakelle', 'saunaofen']
    
    heizung_keywords = [
        'solarwellrohr', 'solarspeicher', 'solarkollektor', 'flachkollektor',
        'heizkreisverteiler', 'pumpengruppe', 'pufferspeicher',
        'ausdehnungsgefäß', 'brauchwassermischer', 'holzvergaser',
    ]
    
    for kw in heizung_keywords:
        if kw in name_lower:
            return 'heizung'
    
    for kw in sauna_keywords:
        if kw in name_lower:
            return 'sauna'
    
    # Bei Kamin/Grill: Prüfe Keywords
    kamin_score = sum(1 for kw in kamin_typ_keywords if kw in name_lower)
    grill_score = sum(1 for kw in grill_typ_keywords if kw in name_lower)
    
    if kamin_score > 0 and grill_score == 0:
        return 'kamin'
    if grill_score > 0 and kamin_score == 0:
        return 'grill'
    if kamin_score > grill_score:
        return 'kamin'
    if grill_score > kamin_score:
        return 'grill'
    
    return 'unbekannt'


def is_zubehoer_fuer_kategorie(produkt_kategorie: str, artikel_kategorie: Optional[str], artikel_name: Optional[str], produkt_name: Optional[str] = None, artikel_hersteller: Optional[str] = None, produkt_hersteller: Optional[str] = None) -> bool:
    """
    Prüft ob ein Zubehör-Artikel zur passenden Hauptkategorie gehört.
    ORIENTIERT SICH ÜBERWIEGEND AM PRODUKTNAMEN.
    
    Regeln:
    1. Heizung/Solar-Artikel werden GLOBAL ausgeschlossen
    2. Kamin-Artikel NUR bei Kamin-Produkten
    3. Grill-Artikel NUR bei Grill-Produkten
    4. Keine Überschneidung zwischen Kamin und Grill
    5. Gleicher Hersteller hat Vorrang (wird beim Scoring gemacht)
    6. Gleiches Modell hat Vorrang (wird beim Scoring gemacht)
    """
    if not produkt_kategorie:
        return True  # Keine Kategorie bekannt, alles erlauben
    
    # Normalisiere alle Texte
    prod_kat = produkt_kategorie.lower()
    art_kat = (artikel_kategorie or '').lower()
    art_name = (artikel_name or '').lower()
    combined = art_kat + ' ' + art_name
    artikel_hersteller_lower = (artikel_hersteller or '').lower()
    prod_name_lower = (produkt_name or '').lower()
    produkt_hersteller_lower = (produkt_hersteller or '').lower()
    combined_produkt = prod_kat + ' ' + prod_name_lower
    
    # ========================================
    # 0. GLOBALER AUSSCHLUSS: Heizungstechnik und unpassende Artikel
    # ========================================
    for keyword in GLOBAL_AUSSCHLUSS_KEYWORDS:
        if keyword in combined:
            return False
    
    # ========================================
    # 1. BEREICH DES ARTIKELS erkennen (aus Artikelname + Hersteller)
    # ========================================
    artikel_bereich = detect_bereich_from_name(art_name, artikel_hersteller)
    
    # Heizung/Solar-Artikel: IMMER ausschließen (nie als CS geeignet)
    if artikel_bereich == 'heizung':
        return False
    
    # ========================================
    # 2. BEREICH DES HAUPTPRODUKTS erkennen (aus Produktname + Kategorie)
    # ========================================
    # Kamin-Produkt Erkennung
    kamin_begriffe = ['kaminofen', 'kaminoefen', 'holzofen', 'kamineinsatz', 'küchenofen', 
                      'kuechenofen', 'werkstattofen', 'systemkamin', 'pelletofen', 'pelletkessel']
    is_kamin_produkt = any(k in combined_produkt for k in kamin_begriffe)
    
    is_kamin = any(k in prod_kat for k in ['kaminofen', 'kaminoefen', 'holzofen', 'kamineinsatz', 'küchenofen', 'kuechenofen', 'werkstattofen', 'systemkamin'])
    is_pellet = 'pellet' in prod_kat and 'ofen' in prod_kat
    is_grill = ('grill' in combined_produkt or 'smoker' in combined_produkt or 'bbq' in combined_produkt
                or any(marke in produkt_hersteller_lower for marke in GRILL_ONLY_MARKEN))
    is_sauna = 'sauna' in prod_kat or 'sauna' in prod_name_lower
    
    # ========================================
    # 3. STRIKTE BEREICHS-TRENNUNG (basierend auf Produktnamen!)
    # ========================================
    
    # 3a. KAMIN-Produkt: Kein Grill-Zubehör, keine Grill-Marken
    if is_kamin or is_pellet or is_kamin_produkt:
        # Grill-Bereich-Artikel blockieren
        if artikel_bereich == 'grill':
            return False
        # Sauna-Bereich blockieren
        if artikel_bereich == 'sauna':
            return False
        # UNBEKANNT-Bereich: Nur erlauben wenn gleicher Hersteller
        # (verhindert z.B. Spartherm-Zubehör bei Extraflame-Produkten)
        if artikel_bereich == 'unbekannt':
            gleicher_herst = (artikel_hersteller_lower and produkt_hersteller_lower and
                            artikel_hersteller_lower.strip() == produkt_hersteller_lower.strip())
            if not gleicher_herst:
                return False
        # Gaskamin-Zubehör NUR bei Gaskaminen, nicht bei Pellet-/Holzöfen
        if any(kw in art_name for kw in ['gaskamin', 'gas-kamin', 'gaseinsatz']):
            if not any(kw in combined_produkt for kw in ['gaskamin', 'gas-kamin', 'gaseinsatz']):
                return False
    
    # 3b. GRILL-Produkt: Kein Kamin-Zubehör, keine Kamin-Marken
    if is_grill:
        # Kamin-Bereich-Artikel blockieren
        if artikel_bereich == 'kamin':
            return False
        # Sauna-Bereich blockieren
        if artikel_bereich == 'sauna':
            return False
        # UNBEKANNT-Bereich: Nur erlauben wenn gleicher Hersteller
        # (verhindert Kamin-Hersteller wie Spartherm, Olsberg, Austroflamm etc.)
        if artikel_bereich == 'unbekannt':
            gleicher_herst = (artikel_hersteller_lower and produkt_hersteller_lower and
                            artikel_hersteller_lower.strip() == produkt_hersteller_lower.strip())
            if not gleicher_herst:
                return False
    
    # 3c. SAUNA-Produkt: Nur Sauna-Zubehör
    if is_sauna:
        if artikel_bereich == 'kamin' or artikel_bereich == 'grill':
            return False
    
    # ========================================
    # 4. STRIKTE KAMIN-ZUBEHÖR REGEL:
    # Kamin-Zubehör darf NUR bei Kamin-Produkten zugeordnet werden!
    # ========================================
    if artikel_bereich == 'kamin' and not is_kamin_produkt:
        return False
    
    # ========================================
    # 5. STRIKTE HERSTELLER-BEREICHS-PRÜFUNG:
    # Kamin-only-Marken NUR bei Kamin-Produkten
    # Grill-only-Marken NUR bei Grill-Produkten
    # ========================================
    is_kamin_marke = any(marke in artikel_hersteller_lower or marke in art_name for marke in KAMIN_ONLY_MARKEN)
    is_grill_marke = any(marke in artikel_hersteller_lower or marke in art_name for marke in GRILL_ONLY_MARKEN)
    is_heizung_marke = any(marke in artikel_hersteller_lower or marke in art_name for marke in HEIZUNG_SOLAR_MARKEN)
    
    # Heizung/Solar-Marken: IMMER blockieren
    if is_heizung_marke:
        return False
    
    # Kamin-Marken bei Nicht-Kamin-Produkten blockieren
    if is_kamin_marke and not is_kamin_produkt:
        return False
    
    # Grill-Marken bei Kamin-Produkten blockieren
    if is_grill_marke and (is_kamin or is_pellet or is_kamin_produkt):
        return False
    
    # ========================================
    # 6. MODELL-MATCHING (BIDIREKTIONAL - Grill + Kamin):
    # Wenn ein CS-Artikel ein bekanntes Modell im Namen hat, ist er
    # modell-spezifisch und darf NUR bei Produkten mit dem GLEICHEN Modell
    # zugeordnet werden. CS-Artikel OHNE Modell sind generisch und erlaubt.
    #
    # Regeln:
    # - CS hat Modell, Produkt hat GLEICHES Modell  → ✅ erlaubt
    # - CS hat Modell, Produkt hat ANDERES Modell   → ❌ blockiert
    # - CS hat Modell, Produkt hat KEIN Modell       → ❌ blockiert
    # - CS hat KEIN Modell (generisch)               → ✅ erlaubt
    #
    # Beispiel: Weber Genesis → Weber Genesis Abdeckhaube ✅
    #           Weber Genesis → Weber Lumin Abdeckhaube ❌
    #           Weber Genesis → Weber Grillzange ✅ (generisch)
    #           Thüros IV    → höfats MOON 45 Funkenschutz ❌
    #           Weber Thermometer → Weber Lumin Set ❌
    # ========================================
    artikel_modelle = extract_all_modelle_from_name(art_name, artikel_hersteller)
    
    if artikel_modelle:
        # CS-Artikel ist modell-spezifisch → Produkt MUSS mindestens ein gleiches Modell haben
        produkt_modelle = extract_all_modelle_from_name(produkt_name or '', None)
        
        if not produkt_modelle:
            # Produkt hat kein Modell → modell-spezifischer CS-Artikel passt nicht
            return False
        
        # Mindestens ein Modell muss übereinstimmen
        if not artikel_modelle.intersection(produkt_modelle):
            return False
    
    # ========================================
    # 7. BRENNSTOFF-FILTER:
    # Gas-spezifisches Zubehör NUR bei Gasgrills, nicht bei Holzkohle/Keramik etc.
    # ========================================
    gas_keywords_in_artikel = any(kw in art_name for kw in [
        'gasanschluss', 'gasflasche', 'gasregler', 'gasschlauch',
        'druckminderer', 'gaskartusche', 'lpg', 'gasadapter',
    ])
    if gas_keywords_in_artikel:
        # Nur bei Gas-Produkten erlauben
        is_gas_produkt = any(kw in combined_produkt for kw in [
            'gasgrill', 'gas-grill', 'gasbrenner', 'gas ',
        ])
        if not is_gas_produkt:
            return False
    
    return True


def is_hauptprodukt(produkttyp_str: Optional[str]) -> bool:
    """
    Prüft ob ein Artikel ein Hauptprodukt ist (kein Zubehör).
    Hauptprodukte dürfen NIEMALS als Cross-Selling zugeordnet werden.
    """
    if not produkttyp_str:
        return False
    
    # JSON-Format bereinigen: '["Kaminofen"]' -> 'kaminofen'
    typ_clean = produkttyp_str.lower()
    typ_clean = typ_clean.replace('[', '').replace(']', '').replace('"', '').replace("'", '')
    typ_clean = typ_clean.replace('\\u00fc', 'ü').replace('\\u00e4', 'ä').replace('\\u00f6', 'ö')
    
    # Prüfe ob einer der Hauptprodukt-Typen enthalten ist
    for haupttyp in HAUPTPRODUKT_TYPEN:
        if haupttyp in typ_clean:
            return True
    
    return False


def get_zubehoer_kategorie(produkttyp_str: Optional[str], artikel_name: Optional[str]) -> Optional[str]:
    """
    Ermittelt die Zubehör-Kategorie eines Artikels.
    Wird für die Diversitäts-Garantie verwendet.
    """
    if not produkttyp_str and not artikel_name:
        return None
    
    text = (produkttyp_str or '').lower() + ' ' + (artikel_name or '').lower()
    text = text.replace('\\u00e4', 'ä').replace('\\u00f6', 'ö').replace('\\u00fc', 'ü')
    
    for kategorie, keywords in ZUBEHOER_KATEGORIEN.items():
        for keyword in keywords:
            if keyword in text:
                return kategorie
    
    return 'sonstiges'


def extract_durchmesser_from_name(name: str) -> Optional[float]:
    """
    Extrahiert Durchmesser aus Artikelnamen.
    Beispiele: "Schornstein 130mm", "Rauchrohr DN 150", "Rohr 120 mm"
    """
    if not name:
        return None
    
    name_lower = name.lower()
    
    # Pattern: "130mm", "130 mm", "DN130", "DN 130", "Ø130"
    patterns = [
        r'(\d{2,3})\s*mm',           # 130mm, 130 mm
        r'dn\s*(\d{2,3})',           # DN130, DN 130
        r'ø\s*(\d{2,3})',            # Ø130
        r'durchmesser\s*(\d{2,3})',  # Durchmesser 130
    ]
    
    for pattern in patterns:
        match = re.search(pattern, name_lower)
        if match:
            dm = float(match.group(1))
            # Plausibilitätsprüfung: Rauchrohr-Durchmesser sind typisch 80-250mm
            if 80 <= dm <= 300:
                return dm
    
    return None


def is_durchmesser_relevant(artikel_name: Optional[str], zub_kategorie: str) -> bool:
    """
    Prüft ob ein Artikel durchmesser-relevant ist (Rohre, Schornstein, etc.)
    Für diese Artikel MUSS der Durchmesser zum Produkt passen.
    """
    # Kategorien die durchmesser-relevant sind
    relevant_kategorien = {'rohrelemente', 'anschluss', 'abschluss', 'schornstein'}
    if zub_kategorie in relevant_kategorien:
        return True
    
    # Keywords im Artikelnamen die auf Durchmesser-Relevanz hindeuten
    if artikel_name:
        name_lower = artikel_name.lower()
        rohr_keywords = [
            'rauchrohr', 'ofenrohr', 'rohrset', 'längenelement', 'bogen',
            'wandfutter', 'rosette', 'schornstein', 'edelstahlschornstein',
            'mündungsabschluss', 'regenhaube', 'reduzierung', 'erweiterung',
            'anschlussstück', 'knie', 'winkel', 't-stück', 'kapsel',
            'pelletrohr', 'abgasrohr', 'verbindungsstück'
        ]
        for kw in rohr_keywords:
            if kw in name_lower:
                return True
    
    return False


def _shuffle_within_score_groups(articles: List[Dict], rng: random.Random) -> List[Dict]:
    """Shuffelt Artikel NUR innerhalb gleicher Score-Gruppen.
    Dadurch bleibt die Score-Reihenfolge (Hersteller, Modell, Farbe etc.) erhalten,
    aber innerhalb gleicher Relevanz werden unterschiedliche Artikel ausgewählt."""
    from itertools import groupby
    result = []
    for score, group in groupby(articles, key=lambda x: x['score']):
        group_list = list(group)
        rng.shuffle(group_list)
        result.extend(group_list)
    return result


def find_crossselling_articles(
    produkt: pd.Series,
    zubehoer_df: pd.DataFrame,
    kriterien: Dict,
    max_articles: int = 8,
    min_articles: int = 5,
    variation_index: int = 0
) -> Tuple[List[Dict], List[str]]:
    """
    Findet passende Cross-Selling-Artikel für ein Produkt.
    GARANTIERT DIVERSITÄT: Verschiedene Zubehör-Typen werden ausgewählt.
    """
    hinweise = []
    
    # Produktkategorie bestimmen
    produkt_kategorie = get_product_kategorie(produkt)
    
    if not produkt_kategorie:
        hinweise.append("Kategorie nicht erkannt")
        return [], hinweise
    
    # Produkt-Eigenschaften extrahieren
    produkt_marke = get_value(produkt, ['hersteller', 'marke', 'brand', 'manufacturer'])
    produkt_durchmesser = get_numeric_value(produkt, ['durchmesser', 'rauchrohr_durchmesser', 'rohrdurchmesser'])
    produkt_farbe = get_value(produkt, ['farbe korpus', 'farbe_korpus', 'farbe', 'color', 'korpusfarbe'])
    produkt_name = get_value(produkt, ['produktname', 'name', 'bezeichnung', 'title'])
    
    # Alle Zubehör-Artikel sammeln und kategorisieren
    kategorisierte_artikel = {}  # {zubehoer_kategorie: [artikel_liste]}
    
    # Bei Extraflame Pelletöfen: WiFi/FB-Artikel von normaler CS-Selektion ausschließen
    # (werden später als Pflichtartikel eingefügt, Deduplizierung über artikel_id + artikelnummer)
    extraflame_pflicht_ids = set()
    if is_extraflame_pelletofen(produkt_kategorie, produkt_name, produkt_marke):
        extraflame_pflicht_ids = EXTRAFLAME_WIFI_FB_ALL_IDS
    
    for idx, artikel in zubehoer_df.iterrows():
        # Hauptprodukte ausschließen
        artikel_produkttyp = get_value(artikel, ['produkttyp', 'kategorie', 'produktkategorie'])
        if is_hauptprodukt(artikel_produkttyp):
            continue
        
        # KATEGORIE-TRENNUNG: Nur Zubehör aus passender Hauptkategorie!
        artikel_kategorie = get_value(artikel, ['kategorie', 'produktkategorie'])
        artikel_name = get_value(artikel, ['name', 'produktname', 'bezeichnung', 'title', 'artikel'])
        artikel_hersteller = get_value(artikel, ['hersteller', 'marke', 'brand', 'manufacturer'])
        
        # WICHTIG: Übergebe Produktname und Artikel-Hersteller für Raik/Opsinox-Prüfung!
        if not is_zubehoer_fuer_kategorie(produkt_kategorie, artikel_kategorie, artikel_name, produkt_name, artikel_hersteller, produkt_marke):
            continue
        artikel_id = get_value(artikel, ['artikel_id', 'artikelnummer', 'id', 'sku', 'artikelnr'])
        
        if not artikel_id:
            continue
        
        # Extraflame WiFi/FB-Artikel überspringen (werden als Pflichtartikel eingefügt)
        if extraflame_pflicht_ids and artikel_id in extraflame_pflicht_ids:
            continue
        
        # Zubehör-Kategorie bestimmen
        zub_kategorie = get_zubehoer_kategorie(artikel_produkttyp, artikel_name)
        
        # Score berechnen
        score = 0
        artikel_marke = get_value(artikel, ['hersteller', 'marke', 'brand', 'manufacturer'])
        artikel_farbe = get_value(artikel, ['farbe', 'farbe_korpus', 'color', 'korpusfarbe'])
        artikel_durchmesser = get_numeric_value(artikel, ['durchmesser', 'rauchrohr_durchmesser', 'rohrdurchmesser', 'rauchrohr durchmesser'])
        
        # Durchmesser auch aus Artikelname extrahieren (z.B. "Schornstein 130mm")
        if not artikel_durchmesser and artikel_name:
            artikel_durchmesser = extract_durchmesser_from_name(artikel_name)
        
        # Durchmesser-Match (STRIKT für Rohre etc.)
        # Wenn Produkt einen Durchmesser hat, müssen Rohrartikel diesen Durchmesser haben!
        if produkt_durchmesser:
            # Prüfe ob Artikel ein durchmesser-relevanter Artikel ist
            is_rohr_artikel = is_durchmesser_relevant(artikel_name, zub_kategorie)
            
            if is_rohr_artikel:
                if artikel_durchmesser:
                    if artikel_durchmesser == produkt_durchmesser:
                        score += 20  # Hoher Bonus für passenden Durchmesser
                    else:
                        # STRIKT: Falscher Durchmesser = Ausschluss
                        continue
                else:
                    # Rohr-Artikel ohne Durchmesser-Info: Sicherheitsausschluss
                    # (könnte falscher Durchmesser sein)
                    pass  # Erlauben, aber ohne Bonus
        elif artikel_durchmesser and produkt_durchmesser:
            if artikel_durchmesser == produkt_durchmesser:
                score += 15
        
        # FARBE-FILTER für Rauchrohre: Wenn Kaminofen farbe_korpus eine bestimmte Farbe hat,
        # dürfen nur Rauchrohre zugeordnet werden, deren Farbe im Namen zur Produktfarbe passt.
        # Logik: Wenn ein Rauchrohr eine erkennbare Farbe im Namen hat, muss diese
        # mit der Produktfarbe übereinstimmen. Rauchrohre ohne Farbe im Namen sind erlaubt.
        if produkt_farbe and artikel_name and is_rauchrohr_name(str(artikel_name)):
            produkt_farbe_lower = str(produkt_farbe).lower().strip()
            artikel_name_lower = str(artikel_name).lower()
            # Alle bekannten Rauchrohr-Farben
            alle_farben = ['schwarz', 'grau', 'braun', 'weiß', 'weiss', 'elfenbein', 'gussgrau']
            # Welche Farbe hat das Rauchrohr im Namen?
            artikel_farben = [f for f in alle_farben if f in artikel_name_lower]
            if artikel_farben:
                # Rauchrohr hat eine Farbe im Namen → muss zur Produktfarbe passen
                produkt_farbe_match = any(f in produkt_farbe_lower for f in artikel_farben)
                if not produkt_farbe_match:
                    continue
        
        # Hersteller-Match
        # WICHTIG: Gleicher Hersteller hat IMMER Vorrang!
        gleicher_hersteller = False
        if produkt_marke and artikel_marke:
            if str(produkt_marke).lower().strip() == str(artikel_marke).lower().strip():
                gleicher_hersteller = True
                # Bei Grill: Sehr hoher Bonus für gleichen Hersteller (höchste Priorität)
                if is_grill_category(produkt_kategorie):
                    score += 50  # Höchste Priorität bei Grill!
                else:
                    score += 10
        
        # Modell/Größen-Match: CS-Artikel die zur gleichen Größe/Modell passen
        # bekommen einen hohen Score-Bonus (z.B. BGE 2XL → BGE Ascheschieber für 2XLarge)
        artikel_modelle = extract_all_modelle_from_name(str(artikel_name) if artikel_name else '')
        if artikel_modelle and produkt_name:
            produkt_modelle = extract_all_modelle_from_name(produkt_name)
            if produkt_modelle and artikel_modelle.intersection(produkt_modelle):
                score += 30  # Hoher Bonus für passende Größe/Modell
        
        # Farbe-Match
        if produkt_farbe and artikel_farbe:
            if farbe_match(str(produkt_farbe), str(artikel_farbe)):
                score += 5
        
        artikel_info = {
            'artikel_id': str(artikel_id),
            'name': str(artikel_name) if artikel_name else str(artikel_id),
            'score': score,
            'hersteller': str(artikel_marke) if artikel_marke else '',
            'farbe': str(artikel_farbe) if artikel_farbe else '',
            'zubehoer_kategorie': zub_kategorie,
            'gleicher_hersteller': gleicher_hersteller,
        }
        
        if zub_kategorie not in kategorisierte_artikel:
            kategorisierte_artikel[zub_kategorie] = []
        kategorisierte_artikel[zub_kategorie].append(artikel_info)
    
    # Jeden Kategorie-Pool nach Score sortieren
    for kat in kategorisierte_artikel:
        kategorisierte_artikel[kat].sort(key=lambda x: x['score'], reverse=True)
    
    # ========================================
    # DIVERSITÄTS-AUSWAHL: Aus verschiedenen Kategorien auswählen
    # ========================================
    selected = []
    used_artikel_ids = set()
    
    # Prioritäten für diese Produktkategorie laden
    prio_config = KATEGORIE_ZUBEHOER_PRIOS.get(produkt_kategorie)
    if not prio_config:
        # Fallback: Standard-Prioritäten
        prio_config = [
            ('rohrelemente', 2), ('anschluss', 1), ('funkenschutz', 1),
            ('reinigung', 1), ('abschluss', 1), ('sonstiges', 1),
        ]
    
    # Aus jeder Kategorie die gewünschte Anzahl auswählen
    # VARIATION: Bei variation_index > 0 werden die Artikel per Shuffle
    # zufällig gemischt, damit bei erneutem Berechnen andere Artikel kommen.
    rng = random.Random(variation_index) if variation_index > 0 else None
    for zub_kategorie, anzahl in prio_config:
        if zub_kategorie in kategorisierte_artikel:
            pool = kategorisierte_artikel[zub_kategorie]
            available = [a for a in pool if a['artikel_id'] not in used_artikel_ids]
            if available and rng:
                available = _shuffle_within_score_groups(available, rng)
            count = 0
            for artikel in available:
                if artikel['artikel_id'] not in used_artikel_ids:
                    selected.append(artikel)
                    used_artikel_ids.add(artikel['artikel_id'])
                    count += 1
                    if count >= anzahl:
                        break
    
    # Falls noch Platz, aus anderen Kategorien auffüllen
    if len(selected) < max_articles:
        for zub_kategorie, pool in kategorisierte_artikel.items():
            available = [a for a in pool if a['artikel_id'] not in used_artikel_ids]
            if available and rng:
                available = _shuffle_within_score_groups(available, rng)
            for artikel in available:
                if artikel['artikel_id'] not in used_artikel_ids:
                    selected.append(artikel)
                    used_artikel_ids.add(artikel['artikel_id'])
                    if len(selected) >= max_articles:
                        break
            if len(selected) >= max_articles:
                break
    
    # ========================================
    # SORTIERUNG: Gleicher Hersteller hat Vorrang → vorne stehen!
    # Artikel mit gleichem Hersteller kommen zuerst, dann die anderen.
    # ========================================
    selected.sort(key=lambda x: (not x.get('gleicher_hersteller', False), -x['score']))
    
    # ========================================
    # PFLICHTARTIKEL: Installationsservice bei Kaminöfen/Holzöfen
    # ========================================
    if is_kaminofen_category(produkt_kategorie, produkt_name):
        iserv_artikel = {
            'artikel_id': '56421',
            'name': 'Kamin Installationsservice',
            'score': 999,
            'hersteller': '',
            'farbe': '',
            'zubehoer_kategorie': 'service',
        }
        if '56421' not in used_artikel_ids:
            selected.insert(0, iserv_artikel)
    
    # ========================================
    # PFLICHTARTIKEL: Rauchrohrset an Position 2 (nach Installationsservice)
    # NUR bei Kaminofen, Küchenofen, Werkstattofen (NICHT Pelletofen/Kamineinsatz)
    # Sucht passendes "Raik Basic Rauchrohrbogen-Set" nach Durchmesser + Farbe schwarz
    # ========================================
    if is_kaminofen_rauchrohrset_category(produkt_kategorie, produkt_name):
        rauchrohrset = find_rauchrohrset(zubehoer_df, produkt_durchmesser, produkt_farbe)
        if rauchrohrset and rauchrohrset['artikel_id'] not in used_artikel_ids:
            # Position 1 = nach Installationsservice (Position 0)
            insert_pos = 1 if selected and selected[0].get('zubehoer_kategorie') == 'service' else 0
            selected.insert(insert_pos, rauchrohrset)
            used_artikel_ids.add(rauchrohrset['artikel_id'])
    
    # ========================================
    # PFLICHTARTIKEL: Extraflame WiFi-Modul + Fernbedienung
    # NUR bei Extraflame Pelletöfen. Wählt automatisch das passende
    # WiFi-Modul (TC 1.0 oder TC 3.0) und die passende Fernbedienung.
    # Position: nach Installationsservice, vor regulären CS-Artikeln.
    # ========================================
    wifi_artikel, fb_artikel = find_extraflame_wifi_fernbedienung(produkt_kategorie, produkt_name, produkt_marke)
    if wifi_artikel and wifi_artikel['artikel_id'] not in used_artikel_ids:
        # Nach Installationsservice (und ggf. Rauchrohrset) einfügen
        insert_pos = 0
        for i, art in enumerate(selected):
            if art.get('zubehoer_kategorie') in ('service', 'rauchrohrset'):
                insert_pos = i + 1
            else:
                break
        selected.insert(insert_pos, wifi_artikel)
        used_artikel_ids.add(wifi_artikel['artikel_id'])
    if fb_artikel and fb_artikel['artikel_id'] not in used_artikel_ids:
        # Direkt nach WiFi-Modul einfügen
        insert_pos = 0
        for i, art in enumerate(selected):
            if art.get('zubehoer_kategorie') in ('service', 'rauchrohrset', 'extraflame_wifi'):
                insert_pos = i + 1
            else:
                break
        selected.insert(insert_pos, fb_artikel)
        used_artikel_ids.add(fb_artikel['artikel_id'])
    
    if len(selected) < min_articles:
        hinweise.append(f"Nur {len(selected)} Artikel gefunden (min. {min_articles} gewünscht)")
    
    return selected[:max_articles], hinweise


def get_product_kategorie(produkt: pd.Series) -> Optional[str]:
    """Ermittelt die Kategorie eines Produkts."""
    kategorie_cols = ['kategorie', 'produktkategorie', 'category', 'warengruppe', 'produkttyp']
    
    for col in kategorie_cols:
        if col in produkt.index:
            val = produkt[col]
            if pd.notna(val) and str(val).strip():
                return normalize_for_matching(str(val))
    
    # Fallback: aus Produktname extrahieren
    name_cols = ['produktname', 'name', 'bezeichnung', 'title']
    for col in name_cols:
        if col in produkt.index:
            name = str(produkt[col]).lower()
            if 'kaminofen' in name or 'holzofen' in name:
                return 'kaminofen'
            elif 'pelletofen' in name or 'pellet' in name:
                return 'pelletofen'
            elif 'kamineinsatz' in name:
                return 'kamineinsatz'
            elif 'systemkamin' in name:
                return 'systemkamin'
            elif 'küchenofen' in name or 'kuechenofen' in name:
                return 'küchenofen'
            elif 'grill' in name or 'bbq' in name or 'smoker' in name or 'kamado' in name or 'keramikgrill' in name or ('big green' in name and 'egg' in name):
                return 'grill'
    
    return None


def normalize_for_matching(text: str) -> str:
    """Normalisiert Text für Matching."""
    text = text.lower().strip()
    text = text.replace('ö', 'oe').replace('ü', 'ue').replace('ä', 'ae').replace('ß', 'ss')
    text = re.sub(r'[^a-z0-9]', '_', text)
    text = re.sub(r'_+', '_', text)
    return text.strip('_')


def get_value(row: pd.Series, possible_cols: List[str]) -> Optional[str]:
    """Holt ersten verfügbaren Wert aus möglichen Spalten."""
    for col in possible_cols:
        if col in row.index:
            val = row[col]
            if pd.notna(val) and str(val).strip() and str(val).lower() != 'nan':
                return str(val).strip()
    return None


def get_numeric_value(row: pd.Series, possible_cols: List[str]) -> Optional[float]:
    """Holt ersten verfügbaren numerischen Wert aus möglichen Spalten."""
    # Erweiterte Suche: auch nach Teilstrings in Spaltennamen suchen
    for col in possible_cols:
        # Direkte Übereinstimmung
        if col in row.index:
            val = row[col]
            if pd.notna(val):
                try:
                    val_str = str(val)
                    numbers = re.findall(r'[\d.]+', val_str)
                    if numbers:
                        return float(numbers[0])
                except:
                    pass
    
    # Fuzzy-Suche: Spalten die den Suchbegriff enthalten
    for search_term in possible_cols:
        for col in row.index:
            col_lower = str(col).lower().replace('ø', '').replace('ö', 'oe').replace('ü', 'ue').replace('ä', 'ae')
            search_lower = search_term.lower().replace('_', ' ')
            # Prüfe ob Suchbegriff in Spaltenname enthalten
            if search_lower in col_lower or ('rauchrohr' in col_lower and 'mm' in col_lower):
                val = row[col]
                if pd.notna(val):
                    try:
                        val_str = str(val)
                        numbers = re.findall(r'[\d.]+', val_str)
                        if numbers:
                            return float(numbers[0])
                    except:
                        pass
    return None


def is_grill_category(produkt_kategorie: str) -> bool:
    """
    Prüft ob ein Produkt ein Grillprodukt ist.
    Bei Grillprodukten hat der gleiche Hersteller HÖCHSTE PRIORITÄT!
    """
    if not produkt_kategorie:
        return False
    
    kat_lower = produkt_kategorie.lower()
    grill_begriffe = [
        'grill', 'bbq', 'smoker', 'kamado', 'pizzaofen',
        'gasgrill', 'holzkohlegrill', 'keramikgrill', 'pelletgrill',
    ]
    
    for begriff in grill_begriffe:
        if begriff in kat_lower:
            return True
    
    return False


def is_rauchrohr_name(name_lower: str) -> bool:
    """Prüft ob ein Artikelname ein Rauchrohr/Ofenrohr ist (für Farb-Filter)."""
    nl = name_lower.lower()
    return 'rauchrohr' in nl or 'ofenrohr' in nl


def find_rauchrohrset(zubehoer_df: pd.DataFrame, produkt_durchmesser: Optional[float], produkt_farbe: Optional[str] = None) -> Optional[Dict]:
    """
    Findet ein passendes Raik Basic Rauchrohrbogen-Set aus der zubehoer_df.
    Kriterien: Durchmesser passend zum Produkt, Farbe passend zur Produkt-Farbe.
    
    Wird als PFLICHT-Artikel an Position 2 (nach Installationsservice) eingefügt
    bei Kaminofen, Küchenofen, Werkstattofen.
    """
    if zubehoer_df is None:
        return None
    
    # Suche nach "Raik Basic Rauchrohrbogen-Set" im Produktnamen
    name_col = None
    for col in zubehoer_df.columns:
        if col in ['produktname', 'name', 'bezeichnung']:
            name_col = col
            break
    
    if name_col is None:
        return None
    
    id_col = None
    for col in zubehoer_df.columns:
        if col in ['artikel id', 'artikel_id', 'artikelnummer']:
            id_col = col
            break
    
    # Alle Rauchrohrbogen-Sets finden (keine B-Ware)
    candidates = []
    for idx, row in zubehoer_df.iterrows():
        name = str(row.get(name_col, '')).lower()
        if 'rauchrohrbogen-set' not in name or 'raik' not in name:
            continue
        if 'b-ware' in name or 'b ware' in name:
            continue
        
        # Durchmesser aus dem Namen extrahieren
        dm = extract_durchmesser_from_name(name)
        if not dm:
            continue
        
        # Farbe erkennen
        is_schwarz = 'schwarz' in name
        
        artikel_id = str(row.get(id_col, ''))
        if not artikel_id or artikel_id == 'nan':
            continue
        
        candidates.append({
            'artikel_id': artikel_id,
            'name': str(row.get(name_col, '')),
            'durchmesser': dm,
            'is_schwarz': is_schwarz,
            'score': 999,
            'hersteller': 'Raik',
            'farbe': 'schwarz' if is_schwarz else '',
            'zubehoer_kategorie': 'rauchrohrset',
        })
    
    if not candidates:
        return None
    
    # Filtern nach Durchmesser (wenn Produkt-Durchmesser bekannt)
    if produkt_durchmesser:
        matching = [c for c in candidates if c['durchmesser'] == produkt_durchmesser]
        if matching:
            candidates = matching
    
    # Farbe passend zur Produkt-Farbe filtern (STRIKT)
    if produkt_farbe:
        pf = str(produkt_farbe).lower().strip()
        for farbe_kw in ['schwarz', 'grau', 'braun']:
            if farbe_kw in pf:
                farb_match = [c for c in candidates if farbe_kw in c['name'].lower()]
                if farb_match:
                    candidates = farb_match
                break
    else:
        # Kein Produkt-Farbe bekannt: Bevorzuge schwarz (Fallback)
        schwarz = [c for c in candidates if c['is_schwarz']]
        if schwarz:
            candidates = schwarz
    
    # Erstes passendes Set zurückgeben
    return candidates[0] if candidates else None


def is_kaminofen_rauchrohrset_category(produkt_kategorie: str, produkt_name: Optional[str]) -> bool:
    """
    Prüft ob ein Produkt ein Kaminofen/Küchenofen/Werkstattofen ist.
    NUR diese Kategorien bekommen ein Rauchrohrset als Pflichtartikel an Position 2.
    NICHT Pelletofen (andere Rohre), NICHT Kamineinsatz.
    """
    begriffe = [
        'kaminofen', 'kaminoefen', 'holzofen', 'holzoefen',
        'werkstattofen', 'werkstattoefen',
        'kuechenofen', 'küchenofen', 'küchenherd',
    ]
    
    kat_lower = produkt_kategorie.lower() if produkt_kategorie else ''
    name_lower = produkt_name.lower() if produkt_name else ''
    
    for begriff in begriffe:
        if begriff in kat_lower or begriff in name_lower:
            return True
    
    return False


def is_kaminofen_category(produkt_kategorie: str, produkt_name: Optional[str]) -> bool:
    """
    Prüft ob ein Produkt ein Kaminofen/Holzofen ist.
    Für diese Kategorie wird der Installationsservice ISERV (56421) automatisch hinzugefügt.
    """
    kaminofen_begriffe = [
        'kaminofen', 'kaminöfen', 'kaminoefen',
        'holzofen', 'holzöfen', 'holzoefen',
        'werkstattofen', 'werkstattöfen',
        'küchenofen', 'küchenherd', 'kuechenofen',
        'systemkamin', 'systemkamine',
        'kamineinsatz', 'kamineinsätze', 'kamineinsaetze',
        'pelletofen', 'pelletöfen', 'pelletoefen',
        'wasserführend', 'wasserfuehrend',
    ]
    
    kat_lower = produkt_kategorie.lower() if produkt_kategorie else ''
    name_lower = produkt_name.lower() if produkt_name else ''
    
    for begriff in kaminofen_begriffe:
        if begriff in kat_lower or begriff in name_lower:
            return True
    
    return False


def is_same_product_category(produkt_kategorie: str, produkt_name: Optional[str], 
                             artikel_produkttyp: Optional[str], artikel_name: Optional[str]) -> bool:
    """
    Prüft ob ein Zubehör-Artikel zur gleichen Produktkategorie gehört wie das Hauptprodukt.
    Wenn ja, muss dieser Artikel AUSGESCHLOSSEN werden (kein Kaminofen als CS für Kaminofen).
    """
    # Liste der Hauptprodukt-Kategorien die ausgeschlossen werden müssen
    hauptprodukt_kategorien = [
        'kaminofen', 'kaminöfen', 'kaminoefen', 'holzofen', 'holzöfen',
        'pelletofen', 'pelletöfen', 'pelletoefen',
        'kamineinsatz', 'kamineinsätze', 'kamineinsaetze',
        'systemkamin', 'systemkamine',
        'küchenofen', 'küchenherd', 'kuechenofen',
        'gaskamin', 'gaskamine',
        'gasgrill', 'holzkohlegrill', 'keramikgrill', 'grill',
        'saunaofen', 'saunaöfen',
        'holzvergaser', 'pelletkessel', 'kombikessel', 'kessel',
        'pufferspeicher', 'brauchwasserspeicher', 'speicher',
    ]
    
    # Normalisiere alle Eingaben
    prod_kat_lower = produkt_kategorie.lower() if produkt_kategorie else ''
    prod_name_lower = produkt_name.lower() if produkt_name else ''
    art_typ_lower = artikel_produkttyp.lower() if artikel_produkttyp else ''
    art_name_lower = artikel_name.lower() if artikel_name else ''
    
    # Finde welche Hauptkategorie das Produkt hat
    produkt_hauptkat = None
    for kat in hauptprodukt_kategorien:
        if kat in prod_kat_lower or kat in prod_name_lower:
            produkt_hauptkat = kat
            break
    
    if not produkt_hauptkat:
        return False  # Keine Hauptkategorie erkannt, kein Ausschluss
    
    # Prüfe ob der Artikel zur gleichen Hauptkategorie gehört
    # Berücksichtige auch JSON-Format wie '["Kaminofen"]'
    art_typ_clean = art_typ_lower.replace('[', '').replace(']', '').replace('"', '').replace("'", "")
    
    for kat in hauptprodukt_kategorien:
        # Wenn Artikel-Typ oder Artikel-Name eine Hauptkategorie enthält
        if kat in art_typ_clean or kat in art_name_lower:
            # Prüfe ob es die GLEICHE Kategorie-Familie ist
            if is_same_category_family(produkt_hauptkat, kat):
                return True  # Gleiche Kategorie → Ausschließen!
    
    return False


def is_same_category_family(kat1: str, kat2: str) -> bool:
    """Prüft ob zwei Kategorien zur gleichen Familie gehören."""
    # Kategorie-Familien definieren
    familien = [
        # Kaminöfen-Familie (inkl. Holzöfen)
        {'kaminofen', 'kaminöfen', 'kaminoefen', 'holzofen', 'holzöfen', 'holzoefen'},
        # Pelletöfen-Familie
        {'pelletofen', 'pelletöfen', 'pelletoefen'},
        # Kamineinsätze-Familie
        {'kamineinsatz', 'kamineinsätze', 'kamineinsaetze'},
        # Grill-Familie
        {'gasgrill', 'holzkohlegrill', 'keramikgrill', 'grill'},
        # Saunaofen-Familie
        {'saunaofen', 'saunaöfen', 'saunaoefen'},
        # Kessel-Familie
        {'holzvergaser', 'pelletkessel', 'kombikessel', 'kessel'},
        # Speicher-Familie
        {'pufferspeicher', 'brauchwasserspeicher', 'speicher', 'schichtenspeicher'},
    ]
    
    for familie in familien:
        kat1_in = any(k in kat1 for k in familie)
        kat2_in = any(k in kat2 for k in familie)
        if kat1_in and kat2_in:
            return True
    
    # Fallback: direkte Übereinstimmung
    return kat1 in kat2 or kat2 in kat1


def farbe_match(farbe1: str, farbe2: str) -> bool:
    """Prüft ob zwei Farben übereinstimmen (fuzzy)."""
    f1 = farbe1.lower().strip()
    f2 = farbe2.lower().strip()
    
    if f1 == f2:
        return True
    
    # Einfaches Fuzzy-Matching für Farbgruppen
    farb_gruppen = {
        'schwarz': ['schwarz', 'black', 'anthrazit', 'dunkel'],
        'weiss': ['weiß', 'weiss', 'white', 'creme'],
        'grau': ['grau', 'grey', 'gray', 'silber'],
        'rot': ['rot', 'red', 'bordeaux', 'weinrot'],
        'braun': ['braun', 'brown', 'holz', 'nuss'],
    }
    
    for gruppe, varianten in farb_gruppen.items():
        f1_match = any(v in f1 for v in varianten)
        f2_match = any(v in f2 for v in varianten)
        if f1_match and f2_match:
            return True
    
    return False


# Globale Worker-Variablen für Multiprocessing (werden per Initializer gesetzt)
_worker_zubehoer_df = None
_worker_kriterien = None


def _worker_initializer(zubehoer_df, kriterien):
    """Initialisiert globale Daten in jedem Worker-Prozess (einmalig pro Prozess)."""
    global _worker_zubehoer_df, _worker_kriterien
    _worker_zubehoer_df = zubehoer_df
    _worker_kriterien = kriterien


def _process_single_product(args):
    """Verarbeitet ein einzelnes Produkt (Worker-Funktion für parallele Verarbeitung)."""
    enum_idx, produkt, variation_index = args
    articles, hinweise = find_crossselling_articles(
        produkt, _worker_zubehoer_df, _worker_kriterien, variation_index=variation_index
    )
    
    cs_string = ""
    cs_namen = ""
    
    if articles:
        cs_parts = [f"{a['artikel_id']}:Accessory" for a in articles]
        cs_string = ";".join(cs_parts) + ";"
        namen_parts = [a['name'] for a in articles]
        cs_namen = ", ".join(namen_parts)
    
    hinweis_str = "; ".join(hinweise) if hinweise else ""
    return enum_idx, cs_string, cs_namen, hinweis_str


def process_all_products(
    produkte_df: pd.DataFrame,
    zubehoer_df: pd.DataFrame,
    kriterien: Dict,
    progress_callback=None,
    parallel_count: int = 10
) -> pd.DataFrame:
    """
    Verarbeitet alle Produkte und fügt Cross-Selling-Spalten hinzu.
    
    Args:
        produkte_df: DataFrame mit Produkten
        zubehoer_df: DataFrame mit Zubehör
        kriterien: Kriterien-Dict
        progress_callback: Optional Callback für Fortschrittsanzeige
        parallel_count: Anzahl der Zeilen, die parallel verarbeitet werden (Standard: 10)
    
    Returns:
        DataFrame mit neuen Spalten 'crossselling' und 'crossselling_namen'
    """
    result_df = produkte_df.copy()
    
    total = len(produkte_df)
    
    # ========================================
    # VARIATION: Produkte mit gleichem Profil (Kategorie + Durchmesser)
    # bekommen unterschiedliche CS-Artikel durch rotierten Startindex.
    # So bekommt z.B. nicht jeder Kaminofen 150mm den gleichen Aschesauger.
    # ========================================
    profil_counter = {}  # {profil_key: laufender_index}
    variation_indices = []
    
    for idx, produkt in produkte_df.iterrows():
        kat = get_product_kategorie(produkt)
        dm = get_numeric_value(produkt, ['durchmesser', 'rauchrohr_durchmesser', 'rohrdurchmesser'])
        profil_key = f"{kat or 'unknown'}_{dm or 'nodm'}"
        vi = profil_counter.get(profil_key, 0)
        variation_indices.append(vi)
        profil_counter[profil_key] = vi + 1
    
    # Ergebnis-Arrays initialisieren
    crossselling_list = [""] * total
    crossselling_namen_list = [""] * total
    hinweise_list = [""] * total
    
    # Worker-Argumente vorbereiten (ohne zubehoer_df/kriterien — die kommen per Initializer)
    worker_args = []
    for enum_idx, (idx, produkt) in enumerate(produkte_df.iterrows()):
        worker_args.append((enum_idx, produkt, variation_indices[enum_idx]))
    
    # Parallele Verarbeitung mit ProcessPoolExecutor (echte Parallelität, umgeht GIL)
    completed = 0
    with ProcessPoolExecutor(
        max_workers=parallel_count,
        initializer=_worker_initializer,
        initargs=(zubehoer_df, kriterien)
    ) as executor:
        futures = {executor.submit(_process_single_product, args): args[0] for args in worker_args}
        
        for future in as_completed(futures):
            enum_idx, cs_string, cs_namen, hinweis_str = future.result()
            crossselling_list[enum_idx] = cs_string
            crossselling_namen_list[enum_idx] = cs_namen
            hinweise_list[enum_idx] = hinweis_str
            
            completed += 1
            if progress_callback:
                progress = completed / total
                progress_callback(progress, f"Verarbeite {completed}/{total}")
    
    result_df['crossselling'] = crossselling_list
    result_df['crossselling_namen'] = crossselling_namen_list
    result_df['cs_hinweis'] = hinweise_list
    
    return result_df
