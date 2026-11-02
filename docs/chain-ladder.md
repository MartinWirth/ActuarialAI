# Chain Ladder – klassische Schadenreservierung

## 1. Ziel und Grundidee

Die **Chain-Ladder-Methode** schätzt aus einem historischen Schadendreieck die noch ausstehenden Zahlungen für bereits entstandene Schäden. Die Methode verwendet historische **Entwicklungsfaktoren (Link Ratios / Loss Development Factors, LDF)**, um fehlende zukünftige kumulierte Zahlungen zu prognostizieren.

Die klassische Chain-Ladder-Methode liefert eine **Punktschätzung** der Reserven, aber keine statistische Aussage über deren Unsicherheit. Diese wird in ActuarialAI separat mit [Mack Chain Ladder](mack_chain-ladder.md) behandelt.

## 2. Datengrundlage: kumuliertes Schadendreieck

ActuarialAI verwendet ein quadratisches **kumuliertes Paid-Claims-Dreieck**:

- **Zeilen:** Anfalljahre (Origin Years).
- **Spalten:** Entwicklungsperioden (Development Periods).
- **Beobachtete Zellen:** Bis zur jeweiligen Periode kumuliert bezahlte Schäden.
- **Fehlende Zellen rechts unten:** Zukünftige, noch unbekannte kumulierte Zahlungen.

Illustratives Beispiel in **Tausend CHF**:

| Anfalljahr | D1 | D2 | D3 | D4 |
| --- | ---: | ---: | ---: | ---: |
| 2022 | 400 | 650 | 800 | 900 |
| 2023 | 450 | 720 | 880 | |
| 2024 | 500 | 800 | | |
| 2025 | 550 | | | |

Eine Einführung zu Aufbau und Datenformat steht in [Schadendreieck (Claims Triangle)](claims_triangle.md).

## 3. Schritt 1: Entwicklungsfaktoren schätzen

Für jeden Übergang von Entwicklungsperiode `j` zu `j+1` berechnet Chain Ladder einen **volumengewichteten Faktor**:

```text
f[j] = Summe_i C[i,j+1] / Summe_i C[i,j]
```

Es werden nur Anfalljahre verwendet, für die beide Werte beobachtet wurden. Der Faktor wird nicht als einfacher Mittelwert der einzelnen Verhältnisse berechnet.

Im Beispiel:

```text
D1 → D2: (650 + 720 + 800) / (400 + 450 + 500)
         = 2170 / 1350 ≈ 1.6074

D2 → D3: (800 + 880) / (650 + 720)
         = 1680 / 1370 ≈ 1.2263

D3 → D4: 900 / 800 = 1.1250
```

| Übergang | Faktor | Interpretation |
| --- | ---: | --- |
| D1 → D2 | 1,6074 | Etwa 60,74 % zusätzliche kumulierte Zahlungen |
| D2 → D3 | 1,2263 | Etwa 22,63 % zusätzliche kumulierte Zahlungen |
| D3 → D4 | 1,1250 | Etwa 12,50 % zusätzliche kumulierte Zahlungen |

**Hinweis:** Bei einem kleinen Dreieck stützt sich der letzte Faktor nur auf ein einziges beobachtetes Paar und ist entsprechend wenig robust.

## 4. Schritt 2: Schadendreieck vervollständigen

Fehlende Zellen werden rekursiv projiziert:

```text
C_hat[i,j+1] = C_hat[i,j] × f[j]
```

Für das Anfalljahr 2023:

```text
D4 = 880 × 1.125 = 990
```

Für 2024:

```text
D3 = 800 × (1680 / 1370) ≈ 981.0
D4 = D3 × 1.125 ≈ 1103.6
```

Für 2025 werden alle drei Faktoren nacheinander angewendet.

Das Ergebnis ist ein **vollständig prognostiziertes kumuliertes Dreieck**. Beobachtete Werte bleiben unverändert; nur zukünftige Zellen werden ergänzt.

## 5. Schritt 3: Ultimate und Schadenreserve bestimmen

Der **Ultimate-Schaden** ist die letzte kumulierte Zahlung der prognostizierten Dreieckszeile. Die Reserve ist die Differenz zum zuletzt tatsächlich beobachteten kumulierten Betrag:

```text
Ultimate[i]      = prognostizierter letzter kumulierter Wert
LatestPaid[i]    = zuletzt beobachteter kumulierter Wert
Reserve[i]       = Ultimate[i] - LatestPaid[i]
TotalReserve     = Summe_i Reserve[i]
```

Mit den ungerundeten Faktoren ergeben sich für das Beispiel folgende Näherungswerte (Tausend CHF):

| Anfalljahr | Latest Paid | Ultimate | Reserve |
| --- | ---: | ---: | ---: |
| 2022 | 900,0 | 900,0 | 0,0 |
| 2023 | 880,0 | 990,0 | 110,0 |
| 2024 | 800,0 | 1'103,6 | 303,6 |
| 2025 | 550,0 | 1'370,2 | 820,2 |
| **Total** | | | **1'233,8** |

Die ausgewiesenen Werte sind gerundet. Der letzte Entwicklungszeitpunkt **D4 wird als Ultimate angenommen**; ein darüber hinausgehender Tail-Faktor ist in der aktuellen Implementierung nicht vorgesehen.

## 6. Annahmen und Grenzen

Die klassische Chain-Ladder-Methode setzt insbesondere voraus, dass historische Entwicklungsmuster für die zukünftige Schadenabwicklung hinreichend repräsentativ sind.

Zu prüfen sind unter anderem:

- Stabilität von Schadenregulierung und Zahlungsverhalten.
- Vergleichbarkeit der Anfalljahre und des versicherten Portfolios.
- Auswirkungen von Inflation, Grossschäden und Gesetzesänderungen.
- Ausreichende Beobachtungen je Entwicklungsperiode.
- Notwendigkeit einer Tail-Entwicklung nach der letzten Dreiecksspalte.

**Chain Ladder ist eine modellbasierte Schätzung, keine Garantie für die tatsächlichen zukünftigen Zahlungen.**

## 7. Implementierung in ActuarialAI

**Quellcode:** `src/actuarial_ai/reserving.py`  
**Funktion:** `chain_ladder(triangle: pandas.DataFrame) -> dict`

Die Implementierung:

1. Prüft ein quadratisches Dreieck mit mindestens zwei Anfalljahren.
2. Verlangt zusammenhängende beobachtete Zellen und `NaN` in den zukünftigen Zellen.
3. Prüft, dass kumulierte Werte endlich, nichtnegativ und innerhalb der Zeile nicht fallend sind.
4. Berechnet volumen­gewichtete Entwicklungsfaktoren; bei null beobachtetem Volumen wird ein Fehler ausgelöst.
5. Füllt die fehlenden Zellen von links nach rechts.
6. Liefert die Reserven je Anfalljahr und deren Summe.

### Rückgabewerte

| Schlüssel | Inhalt |
| --- | --- |
| `factors` | Pandas Series der Entwicklungsfaktoren (LDF) |
| `completed` | Vervollständigtes Schadendreieck als DataFrame |
| `summary` | DataFrame mit `latest_paid`, `ultimate` und `reserve` je Anfalljahr |
| `total_reserve` | Summe der geschätzten Reserven |

### Python-Beispiel

```python
from pathlib import Path

from actuarial_ai.data_io import load_triangle
from actuarial_ai.reserving import chain_ladder

path = Path("example/claims_triangle.csv")
triangle = load_triangle(path.read_bytes(), path.name)
result = chain_ladder(triangle)

print("Entwicklungsfaktoren:")
print(result["factors"])
print("Vervollständigtes Dreieck:")
print(result["completed"])
print("Reserven je Anfalljahr:")
print(result["summary"])
print("Gesamtreserve:", result["total_reserve"])
```

Die Datei [`example/claims_triangle.csv`](../example/claims_triangle.csv) enthält **synthetische** Beispieldaten.

### Dashboard starten

```powershell
git pull
python -m pip install -e ".[dev]"
ruff check .
python -m pytest -q
streamlit run app.py
```

Im Streamlit-Dashboard kann das Beispieldreieck hochgeladen und die Reserveschätzung untersucht werden.

## 8. Chain Ladder und Mack Chain Ladder im Vergleich

| Eigenschaft | Chain Ladder | Mack Chain Ladder |
| --- | --- | --- |
| Entwicklungsfaktoren | Ja | Ja |
| Ultimate- und Reserveschätzung | Ja | Ja |
| Prozess- und Parameterschätzunsicherheit | Nein | Ja |
| Standardfehler / MSEP | Nein | Ja |
| Näherungsweise Intervalle | Nein | Mit zusätzlicher Normalapproximation |

Die **Punktschätzung bleibt gleich**. Mack ergänzt eine statistische Schätzung der Prognoseunsicherheit, unter zusätzlichen Modellannahmen.

## Fazit

Chain Ladder nutzt die historische Entwicklung kumulierter Schadenzahlungen, um ein unvollständiges Schadendreieck zu vervollständigen. Die Differenz zwischen prognostiziertem Ultimate und bereits bezahlten Schäden ergibt die geschätzte ausstehende Schadenreserve. Für Aussagen zur Unsicherheit ist eine Erweiterung wie Mack Chain Ladder erforderlich.
