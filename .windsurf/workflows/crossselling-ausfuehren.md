---
description: Crossselling-Zuordnung ausführen - Startet die Flask Web App zur automatischen CS-Zuordnung
---

# Crossselling ausführen

## Voraussetzungen
- `data/zubehoer.csv` muss vorhanden sein (Pool aller CS-Artikel)
- `data/crossselling-kriterien.xlsx` muss vorhanden sein

## Schritte

// turbo
1. Starte die Flask Web App:
```
python app.py
```
Die App startet auf http://127.0.0.1:7877

2. Öffne die Browser-Preview für den User.

3. Der User lädt seine Produktliste (.xlsx) in der App hoch und klickt "Cross-Selling berechnen".

4. Das Ergebnis wird automatisch im `outputs/` Ordner gespeichert.

## Hinweise
- Alle Matching-Regeln stehen in `matching.py` und `.windsurf/workflows/crossselling-regeln.md`
- Bei Änderungen an den Regeln: Memory und Workflow `crossselling-regeln.md` aktualisieren
- Score-System: Hersteller +50 (Grill) / +10 (Kamin), Modell/Größe +30, Durchmesser +20, Farbe +5
