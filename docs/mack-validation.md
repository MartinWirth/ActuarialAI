# Mack Chain-Ladder – Referenzvalidierung (Phase 21)

## Ziel

Die Mack-Implementierung in `src/actuarial_ai/mack.py` wird anhand des öffentlich dokumentierten **RAA-Schadendreiecks** gegen die Ergebnisse des etablierten R-Pakets **ChainLadder** geprüft. Die Validierung deckt die Chain-Ladder-Punktschätzung, Standardfehler je Anfalljahr und den aggregierten Mack-Standardfehler ab.

## Referenz und Konfiguration

- Quelle: [ChainLadder: Claims reserving with R – Vignette](https://www.stat.ethz.ch/CRAN/web/packages/ChainLadder/vignettes/ChainLadder.html)
- Referenzaufruf in R: `MackChainLadder(RAA, est.sigma = "Mack")`
- Standardkonfiguration: `alpha = 1`, keine Tail-Entwicklung
- Testdatensatz: [`tests/fixtures/raa_triangle.csv`](../tests/fixtures/raa_triangle.csv)
- Regressionstests: [`tests/test_mack.py`](../tests/test_mack.py)

Der Datensatz enthält zehn Anfalljahre (1981–1990), zehn Entwicklungsperioden und kumulierte Schadenwerte. Die Testfixture wurde aus dem veröffentlichten RAA-Beispiel übernommen. Die Einheiten des Datensatzes werden **nicht** als CHF interpretiert.

## Veröffentlichtes Referenzergebnis

| Kennzahl | R ChainLadder |
| --- | ---: |
| Gesamtreserve (IBNR) | 52'135,23 |
| Mack-Standardfehler gesamt | 26'909,01 |

| Anfalljahr | IBNR, gerundet | Mack S.E., gerundet |
| --- | ---: | ---: |
| 1981 | 0 | 0 |
| 1982 | 154 | 206 |
| 1983 | 617 | 623 |
| 1984 | 1'636 | 747 |
| 1985 | 2'747 | 1'469 |
| 1986 | 3'649 | 2'002 |
| 1987 | 5'435 | 2'209 |
| 1988 | 10'907 | 5'358 |
| 1989 | 10'650 | 6'333 |
| 1990 | 16'339 | 24'566 |

## Testabdeckung

`test_raa_published_reference_regression` prüft:

1. Gesamtreserve mit absoluter Toleranz 0,02 gegenüber dem publizierten Ergebnis.
2. Aggregierten Mack-Standardfehler mit absoluter Toleranz 0,02.
3. Reserve und Standardfehler je Anfalljahr mit Toleranz 0,51, da die Referenztabelle ganze Zahlen ausweist.
4. Konsistenz der Mack-Punktschätzung mit `chain_ladder`.
5. Nichtnegative, endliche Varianzschätzungen, gültige Intervallgrenzen und positive aggregierte Kovarianzkomponente.

`test_raa_confidence_changes_only_intervals` prüft, dass sich bei geändertem Konfidenzniveau die Punktschätzung, MSEP und Standardfehler **nicht** verändern, während sich die Intervallgrenzen erweitern.

Zusätzlich bleiben die bestehenden Tests für synthetische Daten, ungültige Eingaben und degenerierte Varianzextrapolation erhalten.

## Tests lokal ausführen

```powershell
git pull
python -m pip install -e ".[dev]"
ruff check .
python -m pytest -q
```

Nur die Mack-Tests:

```powershell
python -m pytest -q tests/test_mack.py
```

## Einordnung und Grenzen

Die Referenzprüfung ist eine **numerische Regression gegen ein publiziertes Beispiel**. Sie liefert starke Evidenz für die hier implementierte Mack-Konfiguration, ersetzt aber keine umfassende unabhängige Modellvalidierung.

Nicht durch diese Referenzprüfung abgedeckt sind insbesondere:

- Alternative Varianzannahmen oder `alpha`-Konfigurationen.
- Tail-Faktoren, Kalenderjahreseffekte und Abhängigkeiten zwischen Anfalljahren.
- Empirische Überdeckungswahrscheinlichkeiten der im Dashboard angezeigten Normalintervalle.
- Regulatorische Eignung oder produktive aktuarielle Freigabe.

Die Mack-MSEP-Schätzung und die nachgelagerte **Normalapproximation für Intervalle** sind getrennt zu beurteilen.

Siehe auch [Schadendreieck](claims_triangle.md), [Chain Ladder](chain-ladder.md) und [Mack Chain Ladder](mack_chain-ladder.md).


## Phase 22: Mack im konfigurierbaren PDF-Bericht

Im Streamlit-Bereich **Generate configurable portfolio PDF report** kann
**Include Mack uncertainty by segment** aktiviert werden. Die Option
`ReportOptions(include_mack=True)` ergänzt den Bericht um:

- Chain-Ladder-Reserve und Mack-Standardfehler je Portfoliosegment.
- Untere und obere Normalapproximation für das konfigurierte Konfidenzniveau.
- Hinweise zu Varianzannahmen, Tail-Ausschluss und Grenzen.
- Eine explizite Fehlermeldung je Segment, falls Mack mangels Daten nicht schätzbar ist.

**Wichtig:** Es wird kein aggregierter Portfolio-Mack-Standardfehler ausgegeben.
Die Abhängigkeit zwischen Segmenten ist nicht geschätzt; eine naive Addition
der Segmentstandardfehler wäre fachlich nicht gerechtfertigt. Die bereits
vorhandenen Monte-Carlo-Risikokennzahlen sind ein separates, annahmengetriebenes
Modell und dürfen nicht als Mack-Validierung interpretiert werden.

Die neue Option ist Teil des SHA-256-Berichtsfingerprints. Alte Berichte bleiben
unverändert; neue PDFs enthalten die Mack-Sektion nur bei aktivierter Option.
