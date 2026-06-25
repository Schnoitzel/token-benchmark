# Technische Erkenntnisse aus den Real-Task-Runs
**Datum:** 2026-06-25  
**Kontext:** Entdeckt während der Benchmark-Runs mit `real-javafx-ui-fixes` (4 UI-Bugs, echtes Java-Repo)

---

## 1. Pi meldet Token-Nutzung pro Turn — nicht kumulativ

**Entdeckt durch:** `input=1` bzw. `input=2` bei Runs mit vielen Tool-Calls.

**Was passiert:**  
Pi gibt bei `--mode json` für jeden Assistenten-Turn ein eigenes `turn_end`-Event aus. Jedes Event enthält nur die Tokens **dieses einen Turns** — keine laufende Gesamtsumme.

Bei einem Tool-Run mit z.B. 47 Turns:
```
Turn  1: input=500  cacheWrite=3.100  cacheRead=0      output=80
Turn  2: input=200  cacheWrite=0      cacheRead=3.600  output=45
Turn  3: input=150  cacheWrite=0      cacheRead=7.200  output=60
...
Turn 47: input=2    cacheWrite=0      cacheRead=27.000 output=119
```

Der ursprüngliche Parser hat nur den **letzten** `turn_end` gelesen → `input=2`, `cacheRead=27.000`.

**Fix:** Alle `turn_end`-Events summieren:
```python
turn_ends = [e for e in events if e.get("type") == "turn_end"]
inp   = sum(e["message"]["usage"]["input"]      for e in turn_ends)
out   = sum(e["message"]["usage"]["output"]     for e in turn_ends)
c_r   = sum(e["message"]["usage"]["cacheRead"]  for e in turn_ends)
c_w   = sum(e["message"]["usage"]["cacheWrite"] for e in turn_ends)
```

**Konsequenz:** Alle Pi-Ergebnisse aus Tool-Runs vor diesem Fix sind **falsch (zu niedrig bei input, zu hoch bei cacheRead)** und wurden verworfen.

---

## 2. Pi cached auch den User-Prompt selbst (nicht nur den System-Prompt)

**Entdeckt durch:** `input=15` (Sonnet) bzw. `input=3762` (Haiku) bei identischer Aufgabe.

Bei Sonnet/Opus packt Pi **auch den User-Prompt** in den Cache-Block (`cacheWrite`), nicht in `input`. Deshalb zeigt `input` fast null:

```
Turn 1: input=3    cacheWrite=3.451  (System-Prompt + User-Prompt gecacht)
Turn 2: input=1    cacheRead=3.451   (alles aus Cache, nur 1 neues Token)
```

Bei Haiku (kein Caching) landet der User-Prompt dagegen vollständig in `input`.

**Die Zahl ist rückrechenbar:** `input = 3 + (Turns - 1) × 1`. Bei Sonnet: `input=15` → 13 Turns = 12 Tool-Calls. Bei Haiku dagegen landet jede Nachricht vollständig in `input` (kein Caching) — deshalb `input=3.762`.

**Konsequenz:** Das `input`-Feld ist **kein verlässlicher Vergleichswert** zwischen Modellen. `total_tokens` (Summe aller Felder) ist die ehrlichste Metrik — sie zählt alles was durch die API ging.

---

## 3. Pi cached bei Tool-Runs den gesamten Gesprächsverlauf

**Entdeckt durch:** Wachsendes `cacheRead` pro Turn bei längeren Tool-Runs.

Anthropic's Prompt-Caching gilt nicht nur für den System-Prompt — bei langen Konversationen cached Pi auch den bisherigen Gesprächsverlauf (Tool-Calls + Ergebnisse). Dadurch wächst `cacheRead` mit jeder Runde:

- Turn 1: nur System-Prompt gecacht (~3.100 Tokens)
- Turn 10: System-Prompt + 9 vorherige Turns gecacht
- Turn 47: System-Prompt + 46 vorherige Turns gecacht → ~27.000 Tokens

Das erklärt warum der letzte Turn zufällig dieselben `cacheRead`-Zahlen wie **Claude Code's System-Prompt-Overhead** (~27k) zeigte — ein irreführender Zufall.

**Wichtig für den Vergleich:**  
Bei langen Tool-Runs hat Pi durch Caching des Konversationsverlaufs ähnlich hohe `cacheRead`-Zahlen wie Claude Code — aber aus einem anderen Grund:
- **Claude Code:** großer System-Prompt + Tool-Definitionen werden gecacht (~27k konstant)
- **Pi (Tool-Run):** kleiner System-Prompt + wachsender Gesprächsverlauf wird gecacht (steigt mit Anzahl Turns)

---

## 3. Ergebnisse gehen verloren wenn SSE-Verbindung abbricht

**Entdeckt durch:** Claude Code Haiku Run — Änderungen in IntelliJ sichtbar, aber kein JSON gespeichert.

**Ursache:** Das Ergebnis-JSON wurde ursprünglich erst am **Ende** des Generators gespeichert (nach `done`-Event). Bei Verbindungsabbruch oder Seitenreload wurde der Generator abgebrochen → keine Speicherung.

**Fix:** Nach **jedem einzelnen Ergebnis** sofort auf Disk schreiben (`core.py`, `_save()`-Funktion). Das JSON existiert ab diesem Zeitpunkt auf Disk, unabhängig vom Status der Browser-Verbindung.

---

## 4. Pi konvertiert Zeilenenden (CRLF → LF) — modellabhängig

**Entdeckt durch:** `git diff --stat` nach Pi-Runs.

| Modell | Betroffene Dateien |
|--------|-------------------|
| Pi Haiku 4.5 | **156 Dateien** (fast das gesamte Repo) |
| Pi Sonnet 4.6 | 0 Dateien (sauber) |
| Pi Opus 4.8 | 1 Datei (`RestoreAdvancedView.java`) |

Das Windows-Repo verwendet CRLF-Zeilenenden. Pi liest Dateien und schreibt sie mit LF zurück. Das Verhalten ist **nicht deterministisch** — Sonnet verhält sich sauber, Haiku und Opus nicht.

**Bedeutung für die Präsentation:** Selbst bei identischen Prompts und Modellen (Anthropic-API) verhält sich dasselbe Modell je nach Harness-Implementierung anders bezüglich Seiteneffekten.

---

## 5. Timeout-Kalibrierung für Repo-Tasks

**Entdeckt durch:** Pi Opus Timeout nach 300s.

Bei einem echten Repo mit 130 Java-Dateien brauchen Modelle deutlich länger als bei einfachen Tasks:
- Pi Haiku: ~60s
- Pi Sonnet: ~54s  
- Pi Opus: >300s (ursprünglicher Timeout) → auf **600s** erhöht

Claude Code durchsucht zusätzlich `CLAUDE.md` (automatisch geladen) und macht mehr Tool-Calls → tendenziell länger als Pi.

---

## 6. Benchmark-Erkenntnis: Prompt-Präzision beeinflusst beide Harnesses gleich

Alle 6 Modell/Harness-Kombinationen haben Bug 3 (Uhrzeit) und Bug 4 (Spaltenbreiten) unvollständig gelöst — weil der Prompt die Anforderungen nicht vollständig spezifiziert hat.

**Implikation:** Der Token-Overhead-Unterschied zwischen Pi und Claude Code (~7–9×) ist unabhängig von der Ausgabequalität. Bei unpräzisem Prompt liefern beide gleich schlechte Ergebnisse — bei gleichem Qualitätsniveau aber drastisch unterschiedlichen Kosten.
