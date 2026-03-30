# Cross-Selling Zuordnungs-Tool – Workflow

## Übersicht

Dieses Tool liest drei Datenlisten ein, ermittelt anhand vordefinierter Kriterien passende Cross-Selling-Artikel für jedes Produkt und schreibt die Ergebnisse zurück in die hochgeladene Produktliste. Eine lokale GUI-Oberfläche steuert den gesamten Prozess.

---

## Dateien & ihre Rollen

| Datei | Typ | Rolle | Verhalten |
|---|---|---|---|
| `zubehoer.csv` | CSV | Pool aller potenziellen Cross-Selling-Artikel (daraus werden CS-Artikel entnommen) | Bleibt dauerhaft gespeichert; kann vom Nutzer ersetzt werden |
| `kriterien-crossselling.xlsx` | Excel | Kriterien-Regeln: Welche CS-Artikel für welchen Produkttyp + welche Kriterien gelten | Fest, wird nie vom Nutzer geändert |
| `[nutzer-upload].xlsx` | Excel | Produktliste, die CS-Artikel erhalten soll | Wird pro Session vom Nutzer hochgeladen |

---

### Struktur `kriterien-crossselling.xlsx`

Die Kriterien-Datei definiert, welche Crossselling-Artikel für welchen Produkttyp zugeordnet werden sollen.

| Spalte | Inhalt |
|---|---|
| **A** (Produkttyp) | Der Produkttyp des Hauptprodukts (z.B. Holzofen, Pelletofen, Gasgrill, Kamineinsatz, Küchenofen, etc.) |
| **B** (Crossselling 1) | Name des ersten Crossselling-Artikeltyps |
| **C** (Kriterien 1) | Kriterien für Crossselling 1 |
| **D** (Crossselling 2) | Name des zweiten Crossselling-Artikeltyps |
| **E** (Kriterien 2) | Kriterien für Crossselling 2 |
| **F, G, H, I, ...** | Weitere Crossselling-Artikel + Kriterien abwechselnd |

**Beispiel Zeile für Holzofen:**
| Produkttyp | CS 1 | Kriterien 1 | CS 2 | Kriterien 2 | CS 3 | Kriterien 3 | ... |
|---|---|---|---|---|---|---|---|
| Holzofen | Installationsservice für Kamine | Muss immer als crossselling sein | Rauchrohrset | Hersteller von Raik, Durchmesser gleich zum produkt, Farbe Korpus gleich zum produkt | Funkenschutzplatte | Farbe passend zum Korpus | ... |

**Kriterien-Typen:**
- `Muss immer als crossselling sein` → Artikel wird IMMER zugeordnet, keine weiteren Bedingungen
- `Hersteller von Raik` → Nur Artikel mit Hersteller = "Raik"
- `Durchmesser gleich zum produkt` → Rauchrohr-Durchmesser muss mit Produkt übereinstimmen
- `Farbe Korpus gleich zum produkt` → Farbe Korpus muss mit Produkt übereinstimmen
- `Gleicher Hersteller` → Hersteller muss mit Hauptprodukt übereinstimmen

---

### Spalten `zubehoer.csv`

Die Zubehör-Datei enthält alle potenziellen Crossselling-Artikel:

| Spalte | Buchstabe | Inhalt |
|---|---|---|
| Hersteller | A | Hersteller des Artikels |
| Produktname | B | Name des Artikels (Format: Hersteller, Modell, Produktart, Farbe, weitere Spezifikation) |
| kategorie | C | Kategorie des Artikels |
| artikelnummer | D | Artikelnummer |
| artikel id | E | **Wichtig:** Diese ID wird für das Ausgabeformat verwendet |
| URL | F | Produkt-URL |
| produkttyp | G | Produkttyp |
| durchmesser | H | Durchmesser |
| rauchrohr durchmesser | I | Rauchrohr-Durchmesser |
| isActive | J | Aktiv-Status |
| farbe korpus-118 | K | Farbe Korpus |

---

### Nutzer-Upload `[produkte].xlsx`
- Enthält Produkteigenschaften: produktname, kategorie/produkttyp, durchmesser, farbe korpus, etc.
- Bekommt nach der Verarbeitung **zwei neue Spalten** hinzugefügt

---

## GUI-Oberfläche

Die App startet eine lokale Weboberfläche (z. B. mit **Gradio** oder **Streamlit**).

### Aufbau der GUI

```
┌─────────────────────────────────────────────────────────────┐
│  🔥 Cross-Selling Zuordnungs-Tool                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  📦 Zubehör-Datenbank                                       │
│  ┌───────────────────────────────────┐  [Datei ersetzen]    │
│  │ zubehoer.csv ✅ geladen           │                      │
│  │ 10.432 Artikel | zuletzt: heute   │                      │
│  └───────────────────────────────────┘                      │
│                                                             │
│  📋 Produktliste hochladen                                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Datei hier ablegen oder klicken zum Auswählen      │    │
│  │  (.xlsx)                                            │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  [▶ Cross-Selling berechnen]                                │
│                                                             │
│  ── Ergebnisse ──────────────────────────────────────────   │
│  Tabellen-Preview mit allen Produkten + zugeordneten CS     │
│  [📥 Ergebnis-Datei herunterladen]                         │
└─────────────────────────────────────────────────────────────┘
```

### GUI-Elemente im Detail

| Element | Funktion |
|---|---|
| Status-Badge `zubehoer.csv` | Zeigt ob Datei geladen ist, Artikelanzahl, letztes Änderungsdatum |
| Button „Datei ersetzen" | Öffnet Datei-Dialog → ersetzt `zubehoer.csv` lokal, lädt neu in den Speicher |
| Upload-Feld Produktliste | Akzeptiert `.xlsx`; zeigt nach Upload: Dateiname, Zeilenanzahl, Vorschau (erste 5 Zeilen) |
| Button „Cross-Selling berechnen" | Startet den Matching-Algorithmus; Fortschrittsbalken + Log-Ausgabe |
| Tabellen-Preview | Scrollbare Tabelle: Produktname + `crossselling`-Spalte + `crossselling_namen`-Spalte |
| Download-Button | Gibt die bearbeitete `.xlsx` mit den zwei neuen Spalten zurück |

---

## Verarbeitungs-Workflow (Schritt für Schritt)

### Schritt 1 – Dateien einlesen

```
START
│
├── zubehoer.csv einlesen → DataFrame „zubehoer"
│   └── Nur isActive == TRUE / 1 behalten
│
├── kriterien-crossselling.xlsx einlesen → DataFrame „kriterien"
│   └── Zeile 1 = Header, ab Zeile 2 = Daten
│
└── [nutzer-upload].xlsx einlesen → DataFrame „produkte"
```

### Schritt 2 – Produkttyp bestimmen

Für jedes Produkt in `produkte`:
- Lese den Produkttyp aus dem Produktnamen oder der Kategorie-Spalte
- Mappe auf einen der Produkttypen in `kriterien-crossselling.xlsx` Spalte A: `Holzofen`, `Pelletofen`, `Gasgrill`, `Kamineinsatz`, etc.
- Falls keine eindeutige Zuordnung → Produkt überspringen mit Hinweis

### Schritt 3 – Matching-Algorithmus

> **Grundprinzip:** Für jedes Produkt wird in `kriterien-crossselling.xlsx` nachgeschaut, welche Crossselling-Artikel zugeordnet werden sollen. Dann wird für jeden CS-Artikel in `zubehoer.csv` gesucht.

**Beispiel-Szenario:**
Ein Produkt "Extraflame Kaminofen schwarz" mit Rauchrohr-Durchmesser 150mm und Farbe Korpus schwarz:

```
1. Finde den Produkttyp des hochgeladenen Produkts
   → "Kaminofen" oder "Holzofen"

2. Suche in kriterien-crossselling.xlsx die Zeile für diesen Produkttyp
   → Zeile "Holzofen" hat folgende CS-Artikel:
     - Installationsservice für Kamine (Kriterium: "Muss immer als crossselling sein")
     - Rauchrohrset (Kriterium: "Hersteller von Raik, Durchmesser gleich zum produkt, Farbe Korpus gleich zum produkt")
     - Rauchrohr Längenelement (Kriterium: "Hersteller von Raik, Durchmesser gleich zum produkt, Farbe Korpus gleich zum produkt")
     - Funkenschutzplatte (Kriterium: "Farbe passend zum Korpus")
     - Kamingarnitur/Reinigung (Aschesauger)
     - Kaminventilator
     - Kamin Brennstoff

3. FÜR JEDEN Crossselling-Artikeltyp aus der Kriterienliste:
   │
   ├── a. Parse die Kriterien aus der Kriterien-Spalte
   │      Beispiel für "Rauchrohr Längenelement":
   │      - Hersteller = "Raik"
   │      - Durchmesser = 150mm (gleich zum Produkt)
   │      - Farbe Korpus = schwarz (gleich zum Produkt)
   │
   ├── b. Suche in zubehoer.csv nach Artikeln die:
   │      - Im Produktnamen oder Kategorie den CS-Typ enthalten
   │        (z.B. "Rauchrohr" oder "Längenelement")
   │      - UND alle Kriterien erfüllen:
   │        → Spalte A (Hersteller) = "Raik"
   │        → Spalte I (rauchrohr durchmesser) = 150
   │        → Spalte K (farbe korpus) = "schwarz"
   │
   └── c. Wenn gefunden: Nimm die artikel id (Spalte E) des passenden Artikels

4. Spezialfall "Muss immer als crossselling sein":
   → Suche Artikel unabhängig von Durchmesser/Farbe/Hersteller
   → Nur nach dem Produktnamen suchen (z.B. "Installationsservice")

5. Sammle alle gefundenen artikel_ids für dieses Produkt
```

### Schritt 4 – Ausgabe-Spalten befüllen

**Spalte `crossselling`** (Format exakt wie vorgegeben):
```
artikel_id:Accessory;artikel_id:Accessory;artikel_id:Accessory;
```

Beispiel:
```
10045:Accessory;10078:Accessory;10123:Accessory;10200:Accessory;10341:Accessory;
```

**Spalte `crossselling_namen`** (Komma-getrennte Klartextnamen):
```
Ofenrohr 150mm schwarz, Reinigungsset Kaminofen, Glasscheibe 300x200, ...
```

### Schritt 5 – Ergebnis-Datei erzeugen

- Originale Produktliste + zwei neue Spalten
- Dateiname: `[original-dateiname]_crossselling.xlsx`
- Encoding: Standard Excel / openpyxl

---

## Technischer Stack (Empfehlung)

| Komponente | Empfehlung |
|---|---|
| Sprache | Python 3.10+ |
| GUI | Gradio 4.x (alternativ: Streamlit) |
| Excel-Verarbeitung | `openpyxl`, `pandas` |
| Matching-Logik | Reines Python / pandas (kein ML nötig) |
| Start | `python app.py` → Browser öffnet sich automatisch |

### Projektstruktur

```
crossselling-zuordnung/
├── app.py                        # GUI-Einstiegspunkt (Gradio/Streamlit)
├── matching.py                   # Matching-Algorithmus
├── data_loader.py                # Einlesen aller Dateien
├── output_writer.py              # Neue Spalten + Export
├── zubehoer.csv                  # Persistente Zubehör-Datenbank (CS-Artikel-Pool)
├── kriterien-crossselling.xlsx   # Feste Kriterien-Datei
├── uploads/                      # Temporäre Ablage für Nutzer-Uploads
├── outputs/                      # Fertige Ergebnisdateien
└── requirements.txt
```

---

## Fehlerbehandlung & Edge Cases

| Situation | Verhalten |
|---|---|
| Produkttyp nicht in kriterien-crossselling.xlsx gefunden | Zeile überspringen, in Log-Spalte vermerken: „Produkttyp nicht erkannt" |
| Kein passender Artikel in zubehoer.csv gefunden | CS-Typ überspringen, Hinweis loggen |
| `zubehoer.csv` nicht vorhanden beim Start | Fehlermeldung in GUI: „Bitte zuerst zubehoer.csv hinterlegen" |
| Upload-Datei hat falsche Spalten | Fehlermeldung mit Liste der erwarteten Spalten |
| Durchmesser-Wert fehlt im Produkt | Kriterium „Durchmesser gleich zum produkt" überspringen |
| Farbe Korpus fehlt im Produkt | Kriterium „Farbe Korpus gleich zum produkt" überspringen |

---

## Ausgabe-Beispiel (Tabellen-Preview in GUI)

| produktname | hersteller | durchmesser | crossselling | crossselling_namen |
|---|---|---|---|---|
| Kaminofen Austroflamm Clou | Austroflamm | 150 | 10045:Accessory;10078:Accessory;10200:Accessory; | Ofenrohr 150mm schwarz, Wandfutter 150mm, Reinigungsset |
| Pelletofen Edilkamin Sly | Edilkamin | 80 | 20011:Accessory;20034:Accessory;20089:Accessory; | Pellet-Abdeckung, Reinigungsset Pellet, Zünder |

---

## Cross-Selling-Kriterien (aus kriterien-crossselling.xlsx)

> **Alle Kriterien werden aus der Datei `kriterien-crossselling.xlsx` gelesen!**
> Die Datei definiert für jeden Produkttyp, welche CS-Artikel zugeordnet werden sollen und welche Kriterien gelten.

### Produkttypen in der Kriterien-Datei (Spalte A)

- Holzofen
- Pelletofen  
- Kamineinsatz
- Küchenofen
- Wasserführender Pelletofen
- Wasserführender Kamin
- Gasgrill
- Gasgrill Set
- Einbau Gasgrill
- Holzkohlegrill
- Keramikgrill
- Pizzaofen
- Holzsaunaofen
- Elektrosaunaofen
- ... (weitere laut Datei)

### Kriterien-Logik

Die Kriterien in Spalte C, E, G, etc. definieren, wie der passende Artikel in `zubehoer.csv` gefunden wird:

| Kriterium | Bedeutung |
|---|---|
| `Muss immer als crossselling sein` | Artikel wird IMMER zugeordnet, keine weiteren Filter |
| `Hersteller von Raik` | Nur Artikel mit Hersteller = "Raik" (Spalte A in zubehoer.csv) |
| `Durchmesser gleich zum produkt` | rauchrohr durchmesser (Spalte I) muss mit Produkt übereinstimmen |
| `Farbe Korpus gleich zum produkt` | farbe korpus (Spalte K) muss mit Produkt übereinstimmen |
| `Gleicher Hersteller` | Hersteller muss mit Hauptprodukt übereinstimmen |
| `passend zum gasgrill` | Maße/Modell passend |
| `NaN` oder leer | Keine spezifischen Kriterien, nur nach Produktname suchen |

---

## ⚠️ WICHTIGE REGELN: Produktnamen-basierte Bereichstrennung

### GRUNDPRINZIP: Orientierung am PRODUKTNAMEN

Der **Produktname** enthält alle wichtigen Informationen: Hersteller, Produkttyp, Spezifikationen (Farbe, Modell).
Die Zuordnung orientiert sich **überwiegend am Produktnamen** – sowohl des Hauptprodukts als auch des CS-Artikels.
Die Funktion `detect_bereich_from_name()` in `matching.py` erkennt den Bereich primär aus dem Produktnamen.

### 1. Drei-Bereiche-Modell (STRIKTE TRENNUNG, KEINE Überschneidung!)

| Bereich | Produkte | Hersteller (Beispiele) |
|---|---|---|
| **Kamin** | Kaminöfen, Pelletöfen, Schornstein, Rohre, Kamineinsätze | Raik, Opsinox, La Nordica, Holetherm, **Schiedel**, Schindler+Hofmann, Brula, Promat |
| **Grill** | Grills, BBQ, Smoker, Pizzaöfen, Grill-Zubehör | Weber, Big Green Egg, Kamado Joe, Traeger, Thüros, Campingaz, Enders, Outdoorchef, Ooni, etc. |
| **Heizung/Solar** | Solarthermie, Heizungstechnik, Kessel | Sunex, Westech Solar, Austroflex, Daikin, Atmos, Afriso, JA Solar, Hoymiles, etc. |

**Regeln:**
- **Kamin-Artikel** dürfen NUR bei **Kamin-Produkten** als CS erscheinen
- **Grill-Artikel** dürfen NUR bei **Grill-Produkten** als CS erscheinen
- **Heizung/Solar-Artikel** werden **GLOBAL ausgeschlossen** (nie als CS geeignet)
- **Sauna-Artikel** nur bei Sauna-Produkten

### 2. Hersteller-Bereichs-Zuordnung (aus matching.py)

**KAMIN_ONLY_MARKEN** – NUR bei Kaminprodukten erlaubt:
- Raik, Opsinox, La Nordica, Holetherm, **Schiedel**, Schindler+Hofmann, Brula, Promat

**GRILL_ONLY_MARKEN** – NUR bei Grillprodukten erlaubt:
- Weber, Big Green Egg, Kamado Joe, Traeger, Masterbuilt, Campingaz, Thüros, Enders, Outdoorchef, Ooni, Gozney, Moesta, Monolith, The Bastard, Ankerkraut, Axtschlag, Petromax, Feuerhand, höfats, etc.

**HEIZUNG_SOLAR_MARKEN** – NIEMALS als CS:
- Sunex, Westech Solar, Austroflex, Daikin, Atmos, Watts Industries, Afriso, JA Solar, Hoymiles, etc.

### 3. Kamin-Zubehör Keywords (VERBOTEN bei Grills)

- Rauchrohr, Ofenrohr, Pelletrohr, Längenelement, Rohrset
- Rosette, Wandfutter, Glasplatte, Vorlegeplatte, Funkenschutzplatte
- Kamingarnitur, Aschesauger, Schornstein, Kaminventilator
- Grundplatte, Regenkragen, Abdeckblende, Wandkonsole, doppelwandig, einwandig

### 4. Modell-Matching (ALLGEMEIN – Grill + Kamin)

**WICHTIG:** Wenn ein Produkt (Grill ODER Kamin) ein spezifisches **MODELL** im Namen hat:
- **Prio 1:** Hersteller muss übereinstimmen (wird beim Scoring bevorzugt)
- **Prio 2:** Wenn der CS-Artikel ebenfalls ein Modell im Namen hat → Modelle MÜSSEN übereinstimmen!
- CS-Artikel **OHNE Modell** (generisches Zubehör) sind weiterhin erlaubt.

**Beispiele:**
- Weber **Genesis** Grill → Weber **Genesis** Abdeckhaube ✅
- Weber **Genesis** Grill → Weber **Lumin** Abdeckhaube ❌ (anderes Modell!)
- Weber **Genesis** Grill → Weber **Grillzange** ✅ (kein Modell = generisches Zubehör)
- höfats **MOON 45** → höfats **MOON 45** Zubehör ✅
- höfats **MOON 45** → höfats **CUBE** Zubehör ❌ (anderes Modell!)
- Extraflame **Amika EVO** Kaminofen → Extraflame **Amika EVO** Zubehör ✅

**Modell-Erkennung:**
Die Funktion `extract_modell_from_name()` in `matching.py` extrahiert den Modellnamen, indem sie:
1. Bekannte Modelle aus `BEKANNTE_MODELLE` prüft (längste zuerst)
2. Fallback: Hersteller + Produkttyp-Keywords entfernt, Rest = Modellname

**Bekannte Modelle (Auszug aus `BEKANNTE_MODELLE` in matching.py):**
- Weber: Genesis, Spirit, Summit, Lumin, Smokefire, Master-Touch, Performer, Traveler, Pulse
- höfats: MOON, MOON 45, Cube, Ellipse, Bowl, Spin, Cone
- Napoleon: Rogue, Prestige, Phantom, Freestyle
- Enders: Boston, Monroe, Kansas, Chicago, Urban
- Kamin: Amika, Amika EVO, Giusy, Ketty, Melinda, Rossella Plus, etc.

### 5. Hersteller-Priorität und Sortierung

- **Gleicher Hersteller** hat Vorrang (Score +50 bei Grill, +10 bei Kamin)
- **Sortierung in der Ausgabe:** CS-Artikel mit gleichem Hersteller stehen VORNE, danach kommen Artikel von anderen Herstellern
- **Fallback:** Anderer Hersteller aus dem gleichen Bereich, wenn nichts passendes gefunden

**Beispiel:** Big Green Egg Grill → Bevorzugt Big Green Egg Zubehör (vorne), dann andere Grill-Marken (hinten)

---

### Beispiel: Holzofen/Kaminofen Crossselling

Aus `kriterien-crossselling.xlsx` Zeile "Holzofen":

| CS-Artikel | Kriterium |
|---|---|
| Installationsservice für Kamine | Muss immer als crossselling sein |
| Rauchrohrset | Hersteller von Raik, Durchmesser gleich zum produkt, Farbe Korpus gleich zum produkt |
| Rauchrohr, Längenelement | Hersteller von Raik, Durchmesser gleich zum produkt, Farbe Korpus gleich zum produkt |
| Funkenschutzplatte | Farbe passend zum Korpus |
| Kamingarnitur/Reinigung (Aschesauger) | - |
| Vermiculiteplatten, Kaminventilator | - |
| Kamin Brennstoff | - |

---

## Hinweise für die Implementierung

- `kriterien-crossselling.xlsx` wird **nie** durch den Nutzer überschrieben – nur lesend geladen
- `zubehoer.csv` liegt im Projektverzeichnis und wird beim Start geladen
- Die Nutzer-Upload-Datei wird **nicht dauerhaft gespeichert** – nur für die laufende Session in `uploads/`
- Die Ergebnis-Datei enthält **alle Original-Spalten** der hochgeladenen Liste plus die zwei neuen Spalten ganz rechts
- Das Format der `crossselling`-Spalte (`:Accessory;`-Suffix) ist **fest vorgegeben** und darf nicht abweichen
