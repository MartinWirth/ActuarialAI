# Mack Chain-Ladder: Prediction Uncertainty

## Ziel

Die klassische Chain-Ladder-Methode schätzt die erwartete ausstehende Schadenreserve als Differenz zwischen prognostizierten ultimativen und bereits bezahlten kumulierten Schäden. Die Mack-Methode ergänzt diese Punktschätzung um einen **Mean Squared Prediction Error (MSEP)** und einen **Standardfehler (SE)**. Sie beschreibt somit die Unsicherheit der Reserveschätzung unter bestimmten Modellannahmen.

> **Status:** Die Implementierung in ActuarialAI ist eine didaktische Näherung. Die ausgegebenen Intervalle sind keine kalibrierten Prognoseintervalle und nicht für aktuarische Freigaben, Rechnungslegung oder regulatorische Kapitalberechnungen bestimmt.

## 1. Datenbasis

Eingabe ist ein quadratisches, kumuliertes **Paid-Claims-Dreieck** mit Anfalljahren in den Zeilen und Entwicklungsperioden in den Spalten. Beobachtete Werte müssen endlich, nichtnegativ und je Anfalljahr monoton nicht fallend sein; zukünftige Zellen bleiben leer.

Beispiel: [`example/claims_triangle.csv`](../example/claims_triangle.csv) mit synthetischen, realistisch skalierten Werten. Die Daten sind **keine echten Versicherungsdaten**.

## 2. Klassische Chain-Ladder-Punktschätzung

Mit kumulierten Schäden `C[i,j]` lautet der volumen­gewichtete Entwicklungsfaktor:

```text
f[j] = sum_i C[i,j+1] / sum_i C[i,j]
```

Dabei werden nur Anfalljahre berücksichtigt, für die beide Entwicklungsperioden beobachtet wurden. Die letzte beobachtete kumulierte Zahlung eines Anfalljahres wird mit den noch ausstehenden Faktoren bis zur letzten Dreiecksspalte fortgeschrieben.

```text
Reserve[i] = Ultimate[i] - LatestPaid[i]
TotalReserve = sum_i Reserve[i]
```

Die Mack-Erweiterung verändert diese Punktschätzung nicht.

## 3. Zwei Quellen der Unsicherheit

- **Prozessrisiko:** Zukünftige Schadenentwicklungen schwanken zufällig, selbst wenn die wahren Entwicklungsfaktoren bekannt wären.
- **Parameterschätzrisiko:** Die Entwicklungsfaktoren werden aus einer begrenzten historischen Datenmenge geschätzt und sind deshalb unsicher.

Die geschätzte mittlere quadratische Prognoseabweichung (`MSEP`) fasst diese Unsicherheitsquellen zusammen. Der Standardfehler hat dieselbe Einheit wie die Schadenreserve:

```text
SE = sqrt(MSEP)
```

Für die aggregierte Reserve sind zusätzlich gemeinsame Parameterschätzfehler der Anfalljahre zu berücksichtigen, da sie dieselben Entwicklungsfaktoren verwenden.

## 4. Implementierung in ActuarialAI

**Modul:** `src/actuarial_ai/mack.py`  
**Funktion:** `mack_chain_ladder(triangle, confidence=0.95)`

1. Das Dreieck wird mit `validate_triangle` geprüft. Für die Mack-Varianzschätzung sind mindestens vier Anfalljahre erforderlich.
2. `chain_ladder` liefert Entwicklungsfaktoren, vollständige Projektion und Reserven.
3. Je Entwicklungsperiode mit mindestens zwei beobachteten Paaren wird die altersbezogene Varianz `sigma2[j]` aus den mit kumulierten Schäden gewichteten quadrierten Abweichungen der individuellen Link Ratios vom volumen­gewichteten Faktor berechnet. Der Nenner ist die Anzahl der Paare minus eins.
4. Für die letzte Entwicklungsperiode liegt nur ein beobachtetes Paar vor. Die Varianz wird deshalb aus den beiden vorherigen Varianzschätzungen extrapoliert; bei degenerierten Werten wird die Berechnung abgebrochen.
5. Je Anfalljahr wird ein rekursiver MSEP aus fortgeschriebenem bisherigen MSEP sowie Prozess- und Parameterschätzkomponenten berechnet.
6. Für den Gesamt-MSEP werden zusätzlich paarweise Kovarianzterme aus gemeinsam geschätzten Faktoren berücksichtigt.
7. Standardfehler und approximative symmetrische Normalintervalle werden berechnet. Negative untere Grenzen werden auf null gesetzt.

Die implementierte Methode setzt insbesondere eine bedingte Varianz proportional zum kumulierten Schaden und unabhängige Anfalljahre voraus. Es wird **kein Tail-Faktor** nach der letzten Dreiecksspalte geschätzt.

### Rückgabewerte

| Feld | Bedeutung |
| --- | --- |
| `summary` | Tabelle je Anfalljahr: `latest_paid`, `ultimate`, `reserve`, `mack_se`, `lower`, `upper` |
| `sigma2` | Geschätzte Varianzparameter je Entwicklungsperiode |
| `total_reserve` | Summe der klassischen Chain-Ladder-Reserven |
| `total_mse` | Aggregierter geschätzter Mean Squared Prediction Error |
| `total_se` | Quadratwurzel aus `total_mse` |
| `confidence` | Gewähltes nominelles Intervallniveau |
| `total_lower`, `total_upper` | Approximative Grenzen der Gesamtreserve |
| `assumptions` | Kurzbeschreibung der Modellannahmen |

### Intervallberechnung

Mit `z` als Quantil der Standardnormalverteilung gilt näherungsweise:

```text
lower = max(0, reserve - z * SE)
upper = reserve + z * SE
```

Bei 95 % beträgt `z` ungefähr 1,96. Beispiel: Reserve CHF 10 Mio., Standardfehler CHF 1,5 Mio. → approximatives Intervall CHF 7,06 bis 12,94 Mio.

**Wichtig:** Die Mack-Methode ist verteilungsfrei hinsichtlich der Punktschätzung und des MSEP unter ihren Annahmen; die hier zusätzlich verwendete **Normalapproximation** ist eine separate Annahme. Die angezeigten Intervalle besitzen daher keine garantierte tatsächliche Überdeckungswahrscheinlichkeit.

## 5. Anwendung

Lokale Installation und Start:

```powershell
git pull
python -m pip install -e ".[dev]"
ruff check .
python -m pytest -q
streamlit run app.py
```

Nach Anmeldung im Dashboard:

1. `example/claims_triangle.csv` als **Claims triangle (.csv or .xlsx)** hochladen.
2. Unter **Mack Chain-Ladder prediction uncertainty** ein nominelles Niveau von 80 %, 90 %, 95 % oder 99 % wählen.
3. Aggregierten Standardfehler, Intervallgrenzen und die Tabelle pro Anfalljahr betrachten.
4. Unter **Mack variance estimates and assumptions** die altersbezogenen Varianzen und Annahmen prüfen.

Alternativ in Python:

```python
from pathlib import Path

from actuarial_ai.data_io import load_triangle
from actuarial_ai.mack import mack_chain_ladder

path = Path("example/claims_triangle.csv")
triangle = load_triangle(path.read_bytes(), path.name)
result = mack_chain_ladder(triangle, confidence=0.95)
print(result["summary"])
print(result["total_reserve"], result["total_se"])
print(result["total_lower"], result["total_upper"])
```

## 6. Grenzen und Interpretation

- **Keine Prognosegarantie:** Insbesondere die Normalintervalle sind keine kalibrierten prädiktiven Quantile.
- **Modellannahmen:** Unabhängigkeit der Anfalljahre, stabile Entwicklungsmechanismen und die spezifische Varianzstruktur müssen fachlich geprüft werden.
- **Dünne Datenlage:** Die letzte Altersvarianz wird extrapoliert; sehr kleine oder verschwindende Varianzen können die Berechnung unmöglich machen.
- **Nicht modellierte Risiken:** Inflation, Kalenderjahreseffekte, Änderungen in Schadenbearbeitung oder Portfoliozusammensetzung, extreme Grossschäden und Tail-Entwicklung können wesentliche zusätzliche Unsicherheit verursachen.
- **Keine Solvenzmetrik:** Der Mack-Standardfehler und das 99-%-Normalintervall sind nicht mit Solvency-II-Kapital oder einem aufsichtsrechtlichen Risikomass gleichzusetzen.
- **Aggregationsannahmen:** Die in diesem Modul verwendeten Kovarianzterme sind modellbasiert; eine unabhängige Validierung anhand etablierter aktuarieller Referenzimplementierungen ist vor fachlichem Einsatz erforderlich.

## 7. Referenz

Mack, T. (1993). *Distribution-free Calculation of the Standard Error of Chain Ladder Reserve Estimates*. ASTIN Bulletin, 23(2), 213–225.

Die konkrete ActuarialAI-Implementierung und ihre Einschränkungen sind im Quellcode `src/actuarial_ai/mack.py` dokumentiert.
