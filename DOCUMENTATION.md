# Cross-Selling Zuordnungs-Tool – Vollständige Dokumentation

> **Diese Datei enthält alle Regeln, Workflows, Architektur-Entscheidungen und Konfigurationen.**
> Sie dient als zentrale Referenz für Entwickler und Anwender.

---

## Inhaltsverzeichnis

1. [Schnellstart](#1-schnellstart)
2. [Projektstruktur](#2-projektstruktur)
3. [Dateien & Datenquellen](#3-dateien--datenquellen)
4. [GUI-Oberfläche](#4-gui-oberfläche)
5. [Verarbeitungs-Workflow](#5-verarbeitungs-workflow)
6. [Matching-Algorithmus & Regeln](#6-matching-algorithmus--regeln)
7. [Pflichtartikel](#7-pflichtartikel)
8. [Score-System](#8-score-system)
9. [Modell-Matching](#9-modell-matching)
10. [Fehlerbehandlung](#10-fehlerbehandlung)
11. [Konfiguration & Anpassung](#11-konfiguration--anpassung)

---

## 1. Schnellstart

### Voraussetzungen
- **Python 3.10+** (https://python.org)
- Dateien `data/zubehoer.csv` und `data/crossselling-kriterien.xlsx` müssen vorhanden sein

### Starten

```bash
# Im Projektordner:
python app.py
```

Die App:
1. Prüft automatisch ob alle Python-Pakete installiert sind (pandas, openpyxl, gradio)
2. Installiert fehlende Pakete automatisch
3. Startet einen lokalen Webserver auf http://127.0.0.1:7877
4. Öffnet automatisch den Browser
5. Findet automatisch einen freien Port falls 7877 belegt ist

### Beenden
- **Ctrl+C** im Terminal drücken

### Benutzung
1. Produktliste (.xlsx) in der App hochladen
2. "Cross-Selling berechnen" klicken
3. Ergebnis wird in `outputs/` gespeichert und kann heruntergeladen werden

---

## 2. Projektstruktur

```
crossselling-zuordnung/
├── app.py                          # GUI-Einstiegspunkt (Gradio), standalone-fähig
├── matching.py                     # Matching-Algorithmus (Score, Bereiche, Modelle)
├── data_loader.py                  # Einlesen aller Dateien, Spalten-Normalisierung
├── output_writer.py                # Ergebnis als Excel schreiben
├── requirements.txt                # Python-Abhängigkeiten
├── DOCUMENTATION.md                # Diese Datei (zentrale Referenz)
├── WORKFLOW.md                     # Ursprünglicher Workflow (veraltet, siehe hier)
├── data/
│   ├── zubehoer.csv                # Pool aller CS-Artikel (fest, ersetzbar)
│   └── crossselling-kriterien.xlsx # Kriterien-Datei (fest, nie geändert)
├── uploads/                        # Temporäre Nutzer-Uploads
├── outputs/                        # Ergebnis-Dateien
└── test-dateien/                   # Test-Produktlisten
```

---

## 3. Dateien & Datenquellen

### 3.1 `data/zubehoer.csv` – Zubehör-Datenbank (CS-Artikel-Pool)

| Spalte | Inhalt |
|--------|--------|
| Hersteller | Hersteller des Artikels |
| Produktname | Name (enthält Hersteller, Modell, Produktart, Farbe, Spezifikation) |
| kategorie | Kategorie |
| artikelnummer | Artikelnummer |
| artikel id | **Wichtig:** Diese ID wird für das Ausgabeformat verwendet |
| URL | Produkt-URL |
| produkttyp | Produkttyp |
| durchmesser | Durchmesser |
| rauchrohr durchmesser | Rauchrohr-Durchmesser |
| isActive | Aktiv-Status (nur TRUE/1 werden geladen) |
| farbe korpus-118 | Farbe Korpus |

**Hinweis:** Spaltennamen werden beim Laden automatisch auf **lowercase** normalisiert.

### 3.2 `data/crossselling-kriterien.xlsx` – Kriterien-Datei

Definiert welche CS-Artikel für welchen Produkttyp zugeordnet werden.

| Spalte | Inhalt |
|--------|--------|
| Produktkategorie | Produkttyp (z.B. Holzofen, Pelletofen, Gasgrill) |
| Prio 1 Produkt | Erster CS-Artikeltyp |
| Prio 1 Kriterium | Kriterien dafür |
| Prio 2, 3, 4... | Weitere CS-Artikel + Kriterien |

**Kriterien-Typen:**
- `Muss immer als crossselling sein` → Immer zuordnen
- `Hersteller von Raik` → Nur Hersteller = "Raik"
- `Durchmesser gleich zum produkt` → Durchmesser muss passen
- `Farbe Korpus gleich zum produkt` → Farbe muss passen
- `Gleicher Hersteller` → Hersteller muss übereinstimmen

### 3.3 Nutzer-Upload `[produkte].xlsx`

- Enthält Produkteigenschaften: produktname, kategorie/produkttyp, durchmesser, farbe korpus etc.
- Bekommt nach Verarbeitung zwei neue Spalten: `crossselling` und `crossselling_namen`

---

## 4. GUI-Oberfläche

```
┌─────────────────────────────────────────────────────────────┐
│  🔥 Cross-Selling Zuordnungs-Tool                           │
├─────────────────────────────────────────────────────────────┤
│  📦 Zubehör-Datenbank (Status + Upload zum Ersetzen)        │
│  📋 Produktliste hochladen (.xlsx)                           │
│  [▶ Cross-Selling berechnen]                                │
│  ── Ergebnisse ──                                           │
│  Produktliste mit CS-Artikeln + 🔄 Einzelprodukt-Recalc     │
│  [📥 Ergebnis-Datei herunterladen]                          │
└─────────────────────────────────────────────────────────────┘
```

- **🔄-Button:** Berechnet CS für ein einzelnes Produkt neu (mit `random.randint(1, 1000)` als `variation_index`)
- **Server:** Läuft weiter auch wenn Browser-Tab geschlossen wird. Beenden mit Ctrl+C.

---

## 5. Verarbeitungs-Workflow

### Schritt 1 – Dateien einlesen
- `zubehoer.csv` → DataFrame (nur `isActive == TRUE`)
- `crossselling-kriterien.xlsx` → Kriterien-Dict
- Nutzer-Upload `.xlsx` → Produkte-DataFrame

### Schritt 2 – Produkttyp bestimmen
Für jedes Produkt: Kategorie aus Spalte oder Produktname erkennen.
Mapping auf: kaminofen, pelletofen, kamineinsatz, grill, etc.

### Schritt 3 – Matching-Algorithmus
Für jedes Produkt werden passende CS-Artikel aus `zubehoer.csv` gesucht.
Details siehe [Abschnitt 6](#6-matching-algorithmus--regeln).

### Schritt 4 – Ausgabe-Spalten

**Spalte `crossselling`:**
```
artikel_id:Accessory;artikel_id:Accessory;artikel_id:Accessory;
```

**Spalte `crossselling_namen`:**
```
Artikelname 1, Artikelname 2, Artikelname 3
```

### Schritt 5 – Ergebnis-Datei
- Originalname + `_crossselling.xlsx`
- Alle Original-Spalten + zwei neue Spalten rechts
- Gespeichert in `outputs/`

---

## 6. Matching-Algorithmus & Regeln

### GRUNDPRINZIP: Orientierung am PRODUKTNAMEN

Der **Produktname** enthält alle wichtigen Informationen: Hersteller, Produkttyp, Spezifikationen.
Die Funktion `detect_bereich_from_name()` in `matching.py` erkennt den Bereich primär aus dem Produktnamen.

### 6.1 Drei-Bereiche-Modell (STRIKTE TRENNUNG)

| Bereich | Produkte | Hersteller |
|---------|----------|------------|
| **Kamin** | Kaminöfen, Pelletöfen, Schornstein, Rohre, Kamineinsätze | Raik, Opsinox, La Nordica, Holetherm, Schiedel, Schindler+Hofmann, Brula, Promat |
| **Grill** | Grills, BBQ, Smoker, Pizzaöfen, Grill-Zubehör, Keramikgrill | Weber, Big Green Egg, Kamado Joe, Traeger, Thüros, Campingaz, Enders, Outdoorchef, Ooni, höfats, etc. |
| **Heizung/Solar** | Solarthermie, Heizungstechnik, Kessel | Sunex, Westech Solar, Daikin, Atmos, Afriso, JA Solar, etc. |

**Regeln:**
- Kamin-Artikel NUR bei Kamin-Produkten
- Grill-Artikel NUR bei Grill-Produkten
- Heizung/Solar-Artikel werden **GLOBAL ausgeschlossen** (nie als CS)
- KEINE Überschneidung zwischen den Bereichen

### 6.2 Hersteller-Listen (in matching.py)

- **`KAMIN_ONLY_MARKEN`**: Raik, Opsinox, La Nordica, Holetherm, Schiedel, Schindler+Hofmann, Brula, Promat
- **`GRILL_ONLY_MARKEN`**: Weber, Big Green Egg, Kamado Joe, Traeger, Masterbuilt, Campingaz, Thüros, Enders, Outdoorchef, Ooni, Gozney, höfats, Petromax, Feuerhand, etc.
- **`HEIZUNG_SOLAR_MARKEN`**: Sunex, Westech Solar, Austroflex, Daikin, Atmos, Afriso, JA Solar, Hoymiles, etc.

### 6.3 UNBEKANNT-Filter

Artikel mit Bereich "unbekannt" werden bei Grill- **UND** Kamin-Produkten nur erlaubt wenn **gleicher Hersteller**.

### 6.4 Brennstoff-Filter

- Gas-Keywords (gasanschluss, gasflasche, etc.) → NUR bei Gasgrills
- Gaskamin-Keywords → NUR bei Gaskaminen, nicht bei Pellet-/Holzöfen

### 6.5 Rauchrohr Farb-Filter

Wenn ein Kaminofen in `farbe korpus` eine Farbe hat, dürfen **NUR Rauchrohre/Ofenrohre mit dieser Farbe** im Namen zugeordnet werden.

| Beispiel (Produkt: farbe_korpus = "schwarz") | Erlaubt? |
|----------------------------------------------|----------|
| Raik Rauchrohr Emaille 150mm - 500mm **Grau** | ❌ |
| Raik Rauchrohr Emaille 150mm - 1000mm **Braun** | ❌ |
| Raik Rauchrohr Emaille 150mm - 1000mm **Schwarz** | ✅ |
| Raik Rauchrohr 150mm (ohne Farbe im Namen) | ✅ (generisch) |

**Implementierung:**
- `produkt_farbe` wird mit `get_value(produkt, ['farbe korpus', ...])` extrahiert
  - **WICHTIG:** `'farbe korpus'` (mit Leerzeichen) muss ZUERST stehen, weil Excel-Spalte nach lowercase-Normalisierung so heißt
- `is_rauchrohr_name()` prüft ob "rauchrohr" oder "ofenrohr" im Namen
- Bekannte Farben: schwarz, grau, braun, weiß, weiss, elfenbein, gussgrau
- Rauchrohre OHNE Farbe im Namen = erlaubt (generisch)

### 6.6 Keramikgrill als Grill-Kategorie

- `keramikgrill` wird als Grill erkannt (`get_product_kategorie()`)
- `keramikgrill` ist in `HAUPTPRODUKT_TYPEN` (damit BGE Keramikgrills nicht als CS zugeordnet werden)

### 6.7 Diversitäts-Auswahl

Pro Zubehör-Kategorie wird eine begrenzte Anzahl Artikel ausgewählt (z.B. max. 2 Rohrelemente, 1 Reinigung).
Die Kategorie-Prioritäten sind in `KATEGORIE_ZUBEHOER_PRIOS` in `matching.py` definiert.

### 6.8 Variation/Shuffle

- `_shuffle_within_score_groups()` shuffelt Artikel NUR innerhalb gleicher Score-Gruppen
- Score-Reihenfolge (Hersteller, Modell, Farbe, Durchmesser) bleibt IMMER erhalten
- Bei `variation_index > 0` werden verschiedene Artikel gleicher Relevanz ausgewählt
- Der 🔄-Button nutzt `random.randint(1, 1000)` als variation_index
- Produkte mit gleichem Profil (Kategorie + Durchmesser) bekommen automatisch unterschiedliche variation_indices

---

## 7. Pflichtartikel

### 7.1 Installationsservice (Position 1)

**Artikel-ID:** 56421

Folgende Produkttypen bekommen Installationsservice als **ersten** CS-Artikel:
- Kaminofen, Holzofen, Werkstattofen
- Pelletofen (inkl. wasserführend)
- Kamineinsatz
- Küchenofen
- Wasserführender Kamin

Implementiert in `is_kaminofen_category()`.

### 7.2 Rauchrohrset (Position 2)

**NUR bei Kaminofen, Küchenofen, Werkstattofen** (NICHT Pelletofen, NICHT Kamineinsatz).

Sucht "Raik Basic Rauchrohrbogen-Set" in zubehoer.csv:
- Durchmesser muss zum Produkt passen
- Farbe passend zur Produkt-Farbe (strikt)
- Keine B-Ware

**Verfügbare Durchmesser (Artikel-IDs):**

| Durchmesser | Artikel-ID |
|-------------|-----------|
| 120mm | 18435 |
| 130mm | 18437 |
| 150mm | 18438 |
| 160mm | 18439 |
| 180mm | 18440 |
| 200mm | 18441 |

Implementiert in `find_rauchrohrset()` und `is_kaminofen_rauchrohrset_category()`.

### 7.3 Extraflame WiFi-Modul + Fernbedienung

**NUR bei Extraflame Pelletöfen** (inkl. wasserführende Pelletöfen/Pelletkessel).
Position: Nach Installationsservice, vor regulären CS-Artikeln.

**WiFi-Modul (basierend auf Total Control Version):**

| TC-Version | Modelle | WiFi-Modul | Artikel-ID |
|------------|---------|------------|-----------|
| TC 3.0 | Mirka, Noris, Marina Idro, Comfort P70, Katia, Ilary, Angy, Mariella | WiFi-Modul 2022 Grau | 19343 |
| TC 1.0 | Alle anderen (Souvenir, Ketty, Giusy, Annabella, Serafina, Teodora etc.) | WIFI-Modul 2019 Weiß | 19341 |

**Fernbedienung (passend zum WiFi-Modul):**

| TC-Version | Fernbedienung | Artikel-ID |
|------------|---------------|-----------|
| TC 3.0 | Version B | 19573 |
| TC 1.0 | Version A | 19572 |

Fernbedienung mit grafischem Display (19576) = Premium-Option, nicht automatisch zugeordnet.

Implementiert in `is_extraflame_pelletofen()`, `get_extraflame_tc_version()`, `find_extraflame_wifi_fernbedienung()`.

### 7.4 Pflicht-Kategorien bei Kamin-Produkten

Diese 3 Kategorien müssen bei Kaminöfen, Pelletöfen, Kamineinsätzen etc. **IMMER** im CS sein:
- **Aschesauger/Kaminreiniger** (Kategorie `reinigung`)
- **Kaminbesteck/Kamingarnitur** (Kategorie `kamingarnitur`)
- **Kaminventilator** (Kategorie `kaminventilator`)

Diese stehen am **ANFANG** der Prio-Listen in `KATEGORIE_ZUBEHOER_PRIOS`.

### 7.5 Reihenfolge der Pflichtartikel

```
1. Installationsservice (alle Kaminprodukte)
2. Rauchrohrset (nur Kaminofen/Küchenofen/Werkstattofen)
3. Extraflame WiFi-Modul (nur Extraflame Pelletöfen)
4. Extraflame Fernbedienung (nur Extraflame Pelletöfen)
5. Reguläre CS-Auswahl nach Prio-Liste
```

---

## 8. Score-System

| Kriterium | Score-Bonus |
|-----------|------------|
| Gleicher Hersteller (Grill) | +50 |
| Gleicher Hersteller (Kamin) | +10 |
| Gleiches Modell/Größe | +30 |
| Passender Durchmesser | +20 |
| Passende Farbe | +5 |

**Sortierung:** CS-Artikel mit gleichem Hersteller stehen VORNE, dann nach Score absteigend.

---

## 9. Modell-Matching

### 9.1 Allgemeine Regeln (Grill + Kamin)

| Situation | Erlaubt? |
|-----------|----------|
| CS hat Modell, Produkt hat **GLEICHES** Modell | ✅ |
| CS hat Modell, Produkt hat **ANDERES** Modell | ❌ |
| CS hat Modell, Produkt hat **KEIN** Modell | ❌ |
| CS hat **KEIN** Modell (generisch) | ✅ |
| CS hat **MEHRERE** Modelle → mindestens eins muss übereinstimmen | ✅/❌ |

**Beispiele:**
- Weber Genesis Grill → Weber Genesis Abdeckhaube ✅
- Weber Genesis Grill → Weber Lumin Abdeckhaube ❌ (anderes Modell!)
- Weber Genesis Grill → Weber Grillzange ✅ (kein Modell = generisch)
- höfats MOON 45 → höfats MOON 45 Zubehör ✅, höfats CUBE Zubehör ❌

**Modell-Erkennung:** `extract_modell_from_name()` und `extract_all_modelle_from_name()` in `matching.py`.

Bekannte Modelle in `BEKANNTE_MODELLE`:
- **Weber:** Genesis, Spirit, Summit, Lumin, Smokefire, Master-Touch, Performer, Traveler, Pulse
- **höfats:** MOON, MOON 45, Cube, Ellipse, Bowl, Spin, Cone, Beer Box
- **Napoleon:** Rogue, Prestige, Phantom, Freestyle
- **Kamado Joe:** Classic Joe, Big Joe, Joe Jr
- **Kamin:** Amika, Amika EVO, Giusy, Ketty, Melinda, Rossella Plus, etc.

### 9.2 Big Green Egg Größen als Modelle

BGE-Größen: **Mini, MiniMax, Small, Medium, Large, XL/XLarge, 2XL/XXL/XXLarge/2XLarge**

**WICHTIG: BGE-Größen NUR bei BGE-Artikeln erkennen!**
- Stehen in separatem Set `BGE_GROESSEN_MODELLE` (nicht in `BEKANNTE_MODELLE`)
- Werden nur geprüft wenn `_is_bge_name()` True ergibt
- `_is_bge_name()` erkennt: "big green egg", "big green ... egg", "bge"
- Grund: xl, large, medium, small, mini sind zu generisch für andere Hersteller

**Normalisierung** (`BGE_GROESSEN_NORMALISIERUNG`):
- `xl` → `xlarge`
- `2xl`, `xxl`, `xxlarge` → `2xlarge`

**Multi-Größen:** CS-Artikel können mehrere Größen nennen.
Beispiel: "BGE Ascheschieber für XLarge und 2XLarge" → erkennt `{'xlarge', '2xlarge'}`

---

## 10. Fehlerbehandlung

| Situation | Verhalten |
|-----------|-----------|
| Produkttyp nicht erkannt | Zeile überspringen, Hinweis in `cs_hinweis` |
| Kein passender CS-Artikel gefunden | CS-Typ überspringen |
| `zubehoer.csv` nicht vorhanden | Warnung im Terminal + GUI-Hinweis |
| Upload hat falsche Spalten | Fehlermeldung |
| Durchmesser fehlt beim Produkt | Durchmesser-Kriterium überspringen |
| Farbe fehlt beim Produkt | Rauchrohrset bevorzugt schwarz |
| Port belegt | Automatisch nächsten freien Port suchen |
| Pakete fehlen | Automatische Installation |

---

## 11. Konfiguration & Anpassung

### Server-Konfiguration (in app.py)

```python
SERVER_HOST = "127.0.0.1"   # Nur lokal erreichbar
SERVER_PORT = 7877           # Standard-Port
AUTO_OPEN_BROWSER = True     # Browser automatisch öffnen
```

### Neue Hersteller hinzufügen

1. Hersteller in die passende Marken-Liste eintragen:
   - `KAMIN_ONLY_MARKEN` (matching.py)
   - `GRILL_ONLY_MARKEN` (matching.py)
   - `HEIZUNG_SOLAR_MARKEN` (matching.py)
2. Keywords in `detect_bereich_from_name()` hinzufügen
3. Testen: `python -c "from matching import detect_bereich_from_name; print(detect_bereich_from_name('Neuer Artikelname', 'Hersteller'))"`

### Neue Modelle hinzufügen

1. Modellname zu `BEKANNTE_MODELLE` in `matching.py` hinzufügen
2. Bei BGE-Größen: zu `BGE_GROESSEN_MODELLE` hinzufügen
3. Testen: `python -c "from matching import extract_modell_from_name; print(extract_modell_from_name('Produkt Modellname'))"`

### Prio-Reihenfolge anpassen

In `KATEGORIE_ZUBEHOER_PRIOS` in `matching.py`:

```python
# Beispiel Kaminofen:
_KAMINOFEN_PRIOS = [
    ('reinigung', 1),          # PFLICHT
    ('kamingarnitur', 1),      # PFLICHT
    ('kaminventilator', 1),    # PFLICHT
    ('rohrelemente', 2),
    ('abschluss', 1),
    ('funkenschutz', 1),
    ('vermiculite', 1),
    ('brennstoff', 1),
]
```

### Zubehör-Kategorien

| Kategorie | Keywords |
|-----------|----------|
| `reinigung` | aschesauger, kaminreiniger, reinigung, bürste |
| `kamingarnitur` | kamingarnitur, kaminbesteck, kaminset, kaminwerkzeug |
| `kaminventilator` | kaminventilator, ofenventilator, rauchgasventilator |
| `vermiculite` | vermiculite, vermiculiteplatte, feuerraumauskleidung |
| `brennstoff` | anzündhilfe, anzündwolle, anzünder, brennstoff, holzbrikett, kaminholz, brennholz |
| `rohrelemente` | längenelement, bogen, reduzierung, erweiterung, t-stück, rohr |
| `abschluss` | rosette, blindkappe, mündungsabschluss, regenhaube |
| `funkenschutz` | funkenschutz, bodenplatte, grundplatte, glasplatte |
| `abdeckung` | abdeckung, abdeckhaube, thermoschild, blende |

---

## Technischer Stack

| Komponente | Version |
|------------|---------|
| Python | 3.10+ |
| Gradio | 4.x |
| pandas | 2.x |
| openpyxl | 3.x |

### Abhängigkeiten installieren (manuell)

```bash
pip install -r requirements.txt
```

Oder automatisch beim Start von `python app.py`.

---

## Ausgabeformat

**Spalte `crossselling`:**
```
artikel_id:Accessory;artikel_id:Accessory;artikel_id:Accessory;
```

**Beispiel:**
```
56421:Accessory;18438:Accessory;10045:Accessory;10078:Accessory;
```

Das Format mit `:Accessory;`-Suffix ist **fest vorgegeben** und darf nicht abweichen.
