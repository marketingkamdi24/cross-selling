---
description: Crossselling-Zuordnungsregeln - Bereichstrennung, Produktnamen-Orientierung, Hersteller-Zuordnung
---

# Crossselling-Zuordnungsregeln

## GRUNDPRINZIP: Orientierung am PRODUKTNAMEN

Der **Produktname** enthält alle wichtigen Informationen: Hersteller, Produkttyp, Spezifikationen (Farbe, Modell).
Die Zuordnung orientiert sich **überwiegend am Produktnamen** – sowohl des Hauptprodukts als auch des CS-Artikels.

## 1. Drei-Bereiche-Modell (STRIKTE TRENNUNG)

| Bereich | Produkte | Hersteller |
|---------|----------|------------|
| **Kamin** | Kaminöfen, Pelletöfen, Schornstein, Rohre, Kamineinsätze | Raik, Opsinox, La Nordica, Holetherm, Schiedel, Schindler+Hofmann, Brula, Promat |
| **Grill** | Grills, BBQ, Smoker, Pizzaöfen, Grill-Zubehör | Weber, Big Green Egg, Kamado Joe, Traeger, Thüros, Campingaz, Enders, Outdoorchef, Ooni, Gozney, etc. |
| **Heizung/Solar** | Solarthermie, Heizungstechnik, Kessel | Sunex, Westech Solar, Austroflex, Daikin, Atmos, Afriso, JA Solar, etc. |

**Regeln:**
- Kamin-Artikel NUR bei Kamin-Produkten
- Grill-Artikel NUR bei Grill-Produkten
- Heizung/Solar-Artikel werden GLOBAL ausgeschlossen
- KEINE Überschneidung zwischen den Bereichen

## 2. Bereichs-Erkennung aus Produktnamen

Die Funktion `detect_bereich_from_name()` in `matching.py` prüft:
1. **Hersteller im Namen** → Bereich bestimmen (z.B. "Schiedel" = Kamin, "Weber" = Grill)
2. **Produkttyp-Keywords** → Bereich bestimmen (z.B. "Rauchrohr" = Kamin, "Grillrost" = Grill)
3. **Score-Vergleich** bei Mehrdeutigkeit

## 3. Hersteller-Listen (in matching.py)

- `KAMIN_ONLY_MARKEN`: Raik, Opsinox, La Nordica, Holetherm, Schiedel, Schindler+Hofmann, Brula, Promat
- `GRILL_ONLY_MARKEN`: Weber, Big Green Egg, Kamado Joe, Traeger, Thüros, Campingaz, Enders, etc.
- `HEIZUNG_SOLAR_MARKEN`: Sunex, Westech Solar, Austroflex, Daikin, Atmos, etc.

## 4. Modell-Matching (ALLGEMEIN – Grill + Kamin)

Wenn ein Produkt (Grill ODER Kamin) ein spezifisches Modell im Namen hat:
- **Prio 1:** Hersteller muss übereinstimmen (Score-Bonus)
- **Prio 2:** Wenn CS-Artikel ebenfalls ein Modell im Namen hat → Modelle MÜSSEN übereinstimmen
- CS-Artikel OHNE Modell (generisches Zubehör) sind weiterhin erlaubt

Beispiele:
- Weber Genesis Grill → Weber Genesis Abdeckhaube ✅
- Weber Genesis Grill → Weber Lumin Abdeckhaube ❌ (anderes Modell!)
- Weber Genesis Grill → Weber Grillzange ✅ (kein Modell = generisch)
- höfats MOON 45 → höfats MOON 45 Zubehör ✅, höfats CUBE Zubehör ❌

### 4a. Big Green Egg Größen als Modelle

BGE-Größen werden als Modelle behandelt: **Mini, MiniMax, Small, Medium, Large, XL/XLarge, 2XL/XXL/XXLarge/2XLarge**

**WICHTIG: BGE-Größen NUR bei BGE-Artikeln erkennen!**
Die Begriffe xl, large, medium, small, mini sind zu generisch und würden sonst auch bei Nicht-BGE-Artikeln matchen (z.B. "Gozney Dome XL"). Daher:
- BGE-Größen stehen in separatem Set `BGE_GROESSEN_MODELLE` (nicht in `BEKANNTE_MODELLE`)
- Werden nur geprüft wenn `_is_bge_name()` True ergibt ("big green egg", "big green ... egg", oder "bge" im Namen)
- Funktion `_is_bge_name()` erkennt auch Varianten wie "Big Green XLarge Egg"

**Normalisierung** (`BGE_GROESSEN_NORMALISIERUNG` in `matching.py`):
- `xl` → `xlarge`
- `2xl`, `xxl`, `xxlarge` → `2xlarge`

**Multi-Größen in CS-Artikeln:** CS-Artikel können mehrere Größen nennen.
Beispiel: "Big Green Egg Ascheschieber für XLarge und 2XLarge" → erkennt `{'xlarge', '2xlarge'}`
- Big Green Egg 2XL → BGE Ascheschieber für XLarge und 2XLarge ✅ (2xlarge stimmt überein)
- Big Green Egg Medium → BGE Ascheschieber für XLarge und 2XLarge ❌ (medium ≠ xlarge/2xlarge)
- Big Green Egg XL → BGE Grillzange ✅ (kein Modell = generisch)
- Gozney Dome XL → erkennt KEIN Modell (XL ist BGE-spezifisch, kein allgemeines Modell)

### 4b. Score-Bonus für Modell/Größen-Match (+30)

CS-Artikel die das **gleiche Modell/Größe** wie das Produkt haben, bekommen einen **Score-Bonus von +30**.
Dadurch werden größenspezifische BGE-Artikel (Score 80 = 50 Hersteller + 30 Modell) vor generischen BGE-Artikeln (Score 50 = nur Hersteller) priorisiert.

Beispiel BGE 2XL:
- BGE convEGGtor Korb für 2XLarge → Score 80 (50+30) → **vorne**
- BGE Grillbürste (generisch) → Score 50 → dahinter

Die Funktion `extract_all_modelle_from_name()` in `matching.py` extrahiert ALLE Modelle aus einem Namen und normalisiert sie. Die alte `extract_modell_from_name()` gibt weiterhin nur das erste Modell zurück.

## 5. Installationsservice als Pflicht-CS (Position 1)

Folgende Produkttypen bekommen **Installationsservice (Artikel-ID 56421)** automatisch als **ersten** CS-Artikel:
- Kaminofen, Holzofen, Werkstattofen
- **Pelletofen** (inkl. wasserführender Pelletofen)
- **Kamineinsatz**
- **Küchenofen**
- **Wasserführender Kamin**

Implementiert in `is_kaminofen_category()` in `matching.py`.

## 5a. Rauchrohrset als Pflicht-CS (Position 2)

**NUR bei Kaminofen, Küchenofen, Werkstattofen** (NICHT Pelletofen, NICHT Kamineinsatz):

Ein **Raik Basic Rauchrohrbogen-Set** wird automatisch als **zweiter** CS-Artikel eingefügt (nach Installationsservice).

**Matching-Kriterien:**
- Sucht in `zubehoer.csv` nach Produktname `"Raik Basic Rauchrohrbogen-Set"`
- **Durchmesser** muss zum Produkt passen (aus Produktspalte `ø rauchrohr`)
- **Farbe schwarz** bevorzugt
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

Implementiert in `find_rauchrohrset()` und `is_kaminofen_rauchrohrset_category()` in `matching.py`.

## 5b. Extraflame WiFi-Modul + Fernbedienung als Pflicht-CS

**NUR bei Extraflame Pelletöfen** (inkl. wasserführender Pelletöfen und Pelletkessel):

Ein **WiFi-Modul** und eine **Fernbedienung** werden automatisch als Pflicht-CS-Artikel eingefügt (nach Installationsservice, vor regulären CS-Artikeln).

**WiFi-Modul Auswahl** (basierend auf Total Control Version):

| TC-Version | Modelle | WiFi-Modul | Artikel-ID |
|------------|---------|------------|-----------|
| **TC 3.0** | Mirka, Noris, Marina Idro, Comfort P70, Katia, Ilary, Angy, Mariella | WiFi-Modul 2022 Grau | 19343 |
| **TC 1.0** | Alle anderen (Souvenir, Ketty, Giusy, Annabella, Serafina, Teodora, etc.) | WIFI-Modul 2019 Weiß | 19341 |

**Fernbedienung Auswahl** (passend zum WiFi-Modul):

| TC-Version | Fernbedienung | Artikel-ID |
|------------|---------------|-----------|
| **TC 3.0** | Fernbedienung Version B | 19573 |
| **TC 1.0** | Fernbedienung Version A | 19572 |

**Hinweis:** Fernbedienung mit grafischem Display (19576) ist eine Premium-Option für Wandeinbau und wird nicht automatisch zugeordnet.

**Erkennung:** `is_extraflame_pelletofen()` prüft Hersteller + Produktname auf "extraflame" und "pellet".
**TC-Version:** `get_extraflame_tc_version()` prüft ob ein TC 3.0 Modellname im Produktnamen enthalten ist.

Implementiert in `find_extraflame_wifi_fernbedienung()` in `matching.py`.
TC 3.0 Modellnamen: `EXTRAFLAME_TC3_MODELLE` in `matching.py`.

## 5c. Rauchrohr Farb-Filter (Farbe muss zur Produkt-Farbe passen)

Wenn ein Kaminofen in der Spalte **farbe korpus** eine bestimmte Farbe hat, dürfen **NUR Rauchrohre/Ofenrohre mit dieser Farbe im Namen** als CS zugeordnet werden.

**Geprüfte Farben:** schwarz, grau, braun

**Beispiel:** Kaminofen mit farbe_korpus = "schwarz"
- ❌ Raik Rauchrohr / Ofenrohr Emaille 150mm - 500mm **Grau** → blockiert
- ❌ Raik Rauchrohr / Ofenrohr Emaille 150mm - 1000mm **Braun** → blockiert
- ✅ Raik Rauchrohr / Ofenrohr Emaille 150mm - 1000mm **Schwarz** → erlaubt
- ✅ Raik Basic Rauchrohrbogen-Set 150mm **schwarz** 2-teilig → erlaubt

**Gilt für:**
- Alle Artikel mit "rauchrohr" oder "ofenrohr" im Namen (Funktion `is_rauchrohr_name()`)
- Das Pflicht-Rauchrohrset (`find_rauchrohrset()` filtert jetzt strikt nach Produkt-Farbe)

**Wenn keine Farbe beim Produkt angegeben:** Rauchrohrset bevorzugt schwarz (Fallback-Verhalten).

## 6. Mehr Rauchrohre bei allen Kaminprodukten

Bei ALLEN Kamin-Produkten (inkl. Pelletöfen, Kamineinsätze, Küchenöfen) werden **mehr verschiedene Rauchrohr-Typen** als CS hinzugefügt:
- **Längenelement** (verschiedene Längen)
- **Bogen** (verschiedene Winkel)
- **Rosette** (Kategorie `abschluss`)

Umsetzung: `rohrelemente` auf **2** (reduziert von 4) und `abschluss` auf **1** (reduziert von 2) in `KATEGORIE_ZUBEHOER_PRIOS`. Platz für Pflicht-Kategorien.

## 7. Hersteller-Priorität und Sortierung

- Gleicher Hersteller: +50 Score bei Grill, +10 bei Kamin
- **Sortierung in der Ausgabe:** CS-Artikel mit gleichem Hersteller stehen VORNE, dann andere
- Fallback: Anderer Hersteller aus gleichem Bereich

## 8. PFLICHT-Kategorien bei Kamin-Produkten (IMMER dabei!)

Diese 3 CS-Kategorien müssen bei Kaminöfen, Pelletöfen, Kamineinsätzen etc. **IMMER** im Crossselling sein:
- **Aschesauger/Kaminreiniger** (Kategorie `reinigung`)
- **Kaminbesteck/Kamingarnitur** (Kategorie `kamingarnitur`)
- **Kaminventilator** (Kategorie `kaminventilator`)

**Umsetzung:** Diese 3 stehen am **ANFANG** der Prio-Listen, damit sie vor Rohrelementen gewählt werden und nicht durch das 8-Artikel-Limit abgeschnitten werden.

### Prio-Reihenfolge (Kaminofen-Beispiel):
```
1. reinigung (1)       ← PFLICHT
2. kamingarnitur (1)   ← PFLICHT
3. kaminventilator (1) ← PFLICHT
4. rohrelemente (2)
5. abschluss (1)
6. funkenschutz (1)
7. vermiculite (1)
8. brennstoff (1)
```

### Neue ZUBEHOER_KATEGORIEN in matching.py:
| Kategorie | Keywords |
|-----------|----------|
| `reinigung` | aschesauger, kaminreiniger, reinigung, bürste |
| `kamingarnitur` | kamingarnitur, kaminbesteck, kaminset, kaminwerkzeug |
| `kaminventilator` | kaminventilator, ofenventilator, **rauchgasventilator** |
| `vermiculite` | vermiculite, vermiculiteplatte, feuerraumauskleidung |
| `brennstoff` | anzündhilfe, anzündwolle, anzünder, brennstoff, holzbrikett, kaminholz, brennholz |

**Hinweis:** `rauchgasventilator` wurde aus `GLOBAL_AUSSCHLUSS_KEYWORDS` entfernt und zu `kaminventilator` hinzugefügt.

## 9. Keramikgrill als Grill-Kategorie

`keramikgrill` wird als Grill-Produkttyp erkannt:
- In `get_product_kategorie()`: `'keramikgrill'` → `'grill'`
- In `HAUPTPRODUKT_TYPEN`: `'keramikgrill'` hinzugefügt (damit BGE Keramikgrills nicht als CS zugeordnet werden)

## 10. Bei Änderungen

Wenn neue Hersteller oder Produkttypen hinzukommen:
1. Hersteller in die passende Marken-Liste eintragen (KAMIN_ONLY_MARKEN, GRILL_ONLY_MARKEN, HEIZUNG_SOLAR_MARKEN)
2. Neue Produkttyp-Keywords in `detect_bereich_from_name()` hinzufügen
3. Testen mit `python -c "from matching import detect_bereich_from_name; print(detect_bereich_from_name('Neuer Artikelname', 'Hersteller'))"`
