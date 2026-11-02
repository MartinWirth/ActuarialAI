# Phase 23: Aggregierte Mack-Prognoseunsicherheit

## Ziel

Die segmentbezogenen Mack-Standardfehler werden unter einer **explizit angenommenen**
Korrelation der Prognosefehler zu einer Portfolio-Kennzahl zusammengeführt.

**Wichtig:** Mack Chain Ladder schätzt keine Korrelationen zwischen Versicherungssegmenten.
Die hier verwendete Korrelation ist ein Szenarioparameter, keine aus den Daten
kalibrierte Grösse.

## Formel

Für Segmentstandardfehler `SE_i` und eine gemeinsame paarweise Korrelation
`rho` gilt:

```text
Var(Portfolio) = Summe_i SE_i² + 2 rho Summe_{i<j} SE_i SE_j
SE(Portfolio)  = sqrt(Var(Portfolio))
```

Für `n` Segmente ist die Equikorrelationsmatrix nur für
`-1/(n-1) <= rho <= 1` positiv semidefinit. Das Modul prüft diese Grenze.
Das Dashboard bietet als einfache Szenarioauswahl `0 <= rho <= 1`.

Die Gesamtreserve ist die Summe der Segmentreserven. Ein approximatives
Normalintervall wird als `Reserve ± z * SE(Portfolio)` berechnet; die untere
Grenze wird bei null abgeschnitten.

Als **Diversifikationsvergleich** wird `Summe(SE_i) - SE(Portfolio)`
ausgewiesen. Dies ist kein regulatorisch anrechenbarer Diversifikationseffekt
und kein Vergleich mit einer empirisch geschätzten Korrelationsstruktur.

## Bedienung

Im Dashboard unter **Portfolio Mack risk aggregation (assumption-driven)**:

1. Portfolio-CSV hochladen.
2. Angenommene Segmentkorrelation auswählen.
3. **Calculate aggregate Mack uncertainty** aktivieren.
4. Standardfehler, Vergleich bei Unabhängigkeit und Intervall prüfen.

Der konfigurierbare Portfolio-PDF-Bericht verwendet denselben
Korrelationsparameter, sofern **Include Mack uncertainty by segment** aktiv ist.
Die Korrelation wird in der Berichtsidentität (SHA-256) berücksichtigt.

## Implementierung

- `src/actuarial_ai/portfolio_mack.py`: `aggregate_mack`
- `src/actuarial_ai/report_builder.py`: PDF-Aggregation
- `app.py`: Dashboard-Steuerung
- `tests/test_portfolio_mack.py`: Szenariotests
- `tests/test_report_builder.py`: PDF-Regressionstests

Bei einem nicht schätzbaren Segment wird **keine** unvollständige
Portfolioaggregation ausgegeben; stattdessen wird der Fehler gemeldet.

## Einschränkungen

- Korrelationsannahmen sind nicht kalibriert und müssen fachlich begründet werden.
- Die Mack-Standardfehler bleiben modellabhängig und enthalten keinen Tail-Faktor.
- Normalintervalle sind Näherungen ohne garantierte Überdeckungswahrscheinlichkeit.
- Die Aggregation ersetzt keine gemeinsame stochastische Modellierung oder
  unabhängige aktuarielle Prüfung.
- Die bereits vorhandene Monte-Carlo-Risikosimulation ist ein **separates**
  Modell mit anderen Annahmen; ihre Ergebnisse dürfen nicht mit Mack-Standardfehlern
  gleichgesetzt werden.

## Lokale Prüfung

```powershell
git pull
ruff check .
python -m pytest -q
streamlit run app.py
```
