# Schadendreieck (Claims Triangle)

## 1. Was ist ein Schadendreieck?

Ein **Schadendreieck** ist eine zentrale Datenstruktur der Versicherungsmathematik. Es zeigt, wie sich Schäden eines Versicherungsportfolios nach ihrem Anfalljahr über mehrere Entwicklungsperioden entwickeln. Aus den bisher beobachteten Zahlungen werden noch ausstehende Zahlungen und damit Schadenreserven geschätzt.

In **ActuarialAI** wird ein **kumuliertes Paid-Claims-Dreieck** verwendet: Jede Zelle enthält die Summe aller Zahlungen für ein Anfalljahr bis zum Ende der betreffenden Entwicklungsperiode. Die Daten in `example/claims_triangle.csv` sind synthetisch und keine echten Versicherungsdaten.

## 2. Aufbau

- **Zeilen – Anfalljahre (Origin Years):** In welchem Jahr sind die Schäden entstanden?
- **Spalten – Entwicklungsperioden (Development Periods):** Wie lange konnten sich die Schäden seit dem Anfalljahr entwickeln?
- **Zellen:** Kumulierte Schadenzahlungen.
- **Leere Zellen:** Zukünftige Entwicklungsperioden, für die noch keine Beobachtungen vorliegen.

Beispiel in **Tausend CHF**:

| Anfalljahr | D1 | D2 | D3 | D4 |
| --- | ---: | ---: | ---: | ---: |
| 2022 | 400 | 650 | 800 | 900 |
| 2023 | 450 | 720 | 880 | |
| 2024 | 500 | 800 | | |
| 2025 | 550 | | | |

Die älteren Anfalljahre verfügen über mehr beobachtete Entwicklungsperioden. Deshalb bilden die vorhandenen Daten ein Dreieck. Das Beispiel enthält vier Anfalljahre; die tatsächliche Beispieldatei im Repository enthält zehn.

## 3. Kumulierte und inkrementelle Schäden

**Inkrementelle Zahlungen** sind Zahlungen innerhalb einer einzelnen Entwicklungsperiode. **Kumulierte Zahlungen** sind die Summe aller bis dahin geleisteten Zahlungen.

Beispiel für das Anfalljahr 2022:

| Periode | Inkrementell | Kumuliert |
| --- | ---: | ---: |
| D1 | 400 | 400 |
| D2 | 250 | 650 |
| D3 | 150 | 800 |
| D4 | 100 | 900 |

Die Werte sind in Tausend CHF. Für ein kumuliertes Paid-Claims-Dreieck sollten die Werte innerhalb jeder Zeile nicht sinken.

## 4. Wie berechnet Chain Ladder die zukünftigen Werte?

Die klassische **Chain-Ladder-Methode** ermittelt aus den beobachteten Zellen volumen­gewichtete Entwicklungsfaktoren:

```text
f[j] = Summe(C[i,j+1]) / Summe(C[i,j])
```

Dabei werden nur Anfalljahre berücksichtigt, für die beide benachbarten Entwicklungsperioden bekannt sind. Zukünftige kumulierte Schäden werden durch Multiplikation mit den noch ausstehenden Faktoren projiziert.

Im obigen Beispiel ergibt sich für den Übergang von D3 nach D4 aus dem einzigen vollständig beobachteten Paar:

```text
f[D3→D4] = 900 / 800 = 1.125
```

Für 2023 mit D3 = 880 resultiert:

```text
Prognose D4 (2023) = 880 × 1.125 = 990 (Tausend CHF)
```

Der Wert 990 ist **prognostiziert**, nicht beobachtet.

Die Reserve eines Anfalljahres ist:

```text
Reserve[i] = geschätzter Ultimate-Schaden[i] - zuletzt kumuliert bezahlt[i]
Gesamtreserve = Summe aller Anfalljahresreserven
```

## 5. Was ergänzt Mack Chain Ladder?

Die klassische Chain-Ladder-Methode liefert eine **Punktschätzung** der erwarteten Schadenreserve. **Mack Chain Ladder** ergänzt diese um die geschätzte Unsicherheit der Prognose:

- **Prozessrisiko:** Zufällige Schwankungen zukünftiger Schadenzahlungen.
- **Parameterschätzrisiko:** Unsicherheit der aus historischen Daten geschätzten Entwicklungsfaktoren.

Aus diesen Komponenten werden **Mean Squared Prediction Errors (MSEP)** und **Standardfehler** der Reserven geschätzt. ActuarialAI zeigt zusätzlich näherungsweise Normalintervalle an. Diese sind keine garantierten Prognoseintervalle.

Details: [Mack Chain-Ladder – Prediction Uncertainty](mack_chain-ladder.md).

## 6. Weitere Dreieckstypen

| Typ | Inhalt |
| --- | --- |
| **Paid Claims** | Tatsächlich bezahlte Schadensummen |
| **Incurred Claims** | Bezahlte Schäden zuzüglich geschätzter noch offener Schadenbeträge |
| **Reported Claims** | Je nach Definition Anzahl oder Betrag gemeldeter Schäden |
| **Claim Counts** | Anzahl der Schäden |
| **Average Claim Size** | Durchschnittliche Schadenhöhe |

Diese Dreieckstypen sind nicht ohne fachliche Anpassung austauschbar. Die aktuelle ActuarialAI-Import- und Reservierungslogik ist für **kumulierte Paid Claims** ausgelegt.

## 7. Datenformat in ActuarialAI

**Beispieldatei:** [`example/claims_triangle.csv`](../example/claims_triangle.csv)

Das CSV-Format ist **wide**: Die erste Spalte enthält eindeutige Anfalljahr-Labels, die weiteren Spalten Entwicklungsperioden in zeitlicher Reihenfolge.

```csv
origin,D1,D2,D3,D4
2022,400,650,800,900
2023,450,720,880,
2024,500,800,,
2025,550,,,
```

Die Zahlen dieses Mini-Beispiels sind in Tausend CHF. Für die tatsächliche Datei gelten die dort enthaltenen synthetischen Werte ohne automatisch angenommene Währung.

Die Funktion `load_triangle` in `src/actuarial_ai/data_io.py` validiert:

1. Quadratisches Dreieck mit mindestens zwei Anfalljahren.
2. Eindeutige, vorhandene Zeilen- und Spaltenbezeichnungen.
3. Numerische, endliche Werte in allen beobachteten Zellen.
4. Nichtnegative, innerhalb jeder Zeile nicht fallende kumulierte Zahlungen.
5. Leere zukünftige Zellen in der korrekten Dreiecksform.
6. Positives beobachtetes Volumen für die Schätzung der Entwicklungsfaktoren.

## 8. Anwendung im Dashboard

```powershell
git pull
python -m pip install -e ".[dev]"
streamlit run app.py
```

Nach der Anmeldung:

1. Unter **Claims triangle (.csv or .xlsx)** die Datei `example/claims_triangle.csv` hochladen.
2. Das beobachtete kumulierte Dreieck prüfen.
3. Die berechneten Entwicklungsfaktoren und Reserven je Anfalljahr betrachten.
4. Unter **Mack Chain-Ladder prediction uncertainty** die Standardfehler und approximativen Intervalle untersuchen.

Python-Beispiel:

```python
from pathlib import Path

from actuarial_ai.data_io import load_triangle
from actuarial_ai.reserving import chain_ladder

path = Path("example/claims_triangle.csv")
triangle = load_triangle(path.read_bytes(), path.name)
result = chain_ladder(triangle)

print(result["factors"])
print(result["summary"])
print(result["total_reserve"])
```

## 9. Grenzen

Ein Schadendreieck enthält historische aggregierte Informationen. Die daraus geschätzten Reserven können unzuverlässig sein, wenn sich beispielsweise Inflation, Schadenregulierung, Portfoliomix, Grossschadenverhalten oder Meldeverzögerungen wesentlich verändern. Ein Schadendreieck allein ersetzt keine aktuarische Beurteilung. Insbesondere ist die aktuelle ActuarialAI-Implementierung eine **didaktische Demonstration**, kein freigegebenes Reservierungsmodell für Finanzberichterstattung oder regulatorische Zwecke.

## Fazit

Das Schadendreieck verbindet **Anfalljahr**, **Entwicklungsperiode** und **beobachtete kumulierte Schadenzahlungen**. Es ist die Grundlage für die Projektion zukünftiger Zahlungen mit Chain Ladder und für die Quantifizierung ihrer Unsicherheit mit Mack Chain Ladder.
