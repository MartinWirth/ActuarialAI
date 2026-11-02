# Phase 24 – Mack-Korrelationssensitivität

Die neue Funktion `mack_correlation_sensitivity(segments, correlations, confidence)`
zeigt, wie sich die **angenommene** gemeinsame Korrelation zwischen
Segment-Prognosefehlern auf den aggregierten Mack-Standardfehler auswirkt.

Standard-Szenarien: 0, 0.25, 0.50, 0.75 und 1.00.

Ergebnisse pro Szenario:
- Aggregierte Reserve (bei allen Szenarien unverändert)
- Portfolio-Mack-Standardfehler
- Approximative untere und obere Intervallgrenze
- Diversifikationsvergleich zur Summe der Segmentstandardfehler

Im Streamlit-Portfolio-Bereich kann **Run Mack correlation sensitivity**
aktiviert werden. Die Ergebnisse erscheinen als Tabelle, Liniengrafik und
CSV-Download. Im konfigurierbaren PDF kann die zusätzliche Tabelle über
**Include Mack correlation sensitivity** aktiviert werden. Die PDF-Option
ist Teil des Berichts-Fingerprints.

Die Berechnung verwendet dieselbe Equikorrelationsannahme wie Phase 23.
Segment-Mack-Fehler werden nur einmal geschätzt; für die Szenarien wird die
Varianzformel erneut ausgewertet. Wenn ein Segment nicht schätzbar ist, wird
keine unvollständige Portfolio-Sensitivität erzeugt.

**Fachliche Grenzen:** Korrelationen sind nicht aus historischen Daten
kalibriert. Das Ergebnis ist eine Szenarioanalyse, keine empirische
Abhängigkeitsmodellierung oder regulatorische Kapitalanforderung.
Normalintervalle haben keine garantierte Überdeckungswahrscheinlichkeit.

Lokale Prüfung:

```powershell
git pull
ruff check .
python -m pytest -q
streamlit run app.py
```
