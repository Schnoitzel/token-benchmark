# ADR-0002: Pi meldet Token pro Turn — alle turn_end-Events summieren

- **Status:** Akzeptiert
- **Datum:** 2026-06-25
- **Kontext:** Entdeckt während Real-Task-Runs (`real-javafx-ui-fixes`) mit vielen Tool-Calls

## Problem

Der ursprüngliche Parser in `runners.py` las nur das **letzte** `turn_end`-Event
aus Pi's JSONL-Ausgabe. Bei einfachen Nicht-Tool-Runs (1 Turn) war das korrekt.
Bei Tool-Runs mit N Turns lieferte es nur den letzten Mini-Turn:

```
# Beispiel Sonnet, 13 Turns:
Turn  1: input=3,  cacheWrite=3.451, cacheRead=0,     output=54
Turn  2: input=1,  cacheWrite=70,    cacheRead=3.451, output=125
...
Turn 13: input=1,  cacheWrite=0,     cacheRead=5.800, output=21
```

→ Fehlmessung: `input=1`, `cacheRead=5.800` (nur letzter Turn)  
→ Korrekte Summe: `input=15`, `cacheRead=195.506`, `output=2.564`

## Entscheidung

**Alle `turn_end`-Events summieren:**

```python
turn_ends = [e for e in events if e.get("type") == "turn_end"]
inp    = sum(e["message"]["usage"]["input"]      for e in turn_ends)
out    = sum(e["message"]["usage"]["output"]     for e in turn_ends)
c_read = sum(e["message"]["usage"]["cacheRead"]  for e in turn_ends)
c_write= sum(e["message"]["usage"]["cacheWrite"] for e in turn_ends)
cost   = sum(e["message"]["usage"]["cost"]["total"] for e in turn_ends)
```

Antworttext weiterhin aus dem **letzten** `turn_end` (finales Ergebnis).

## Befunde zur Token-Struktur bei Tool-Runs

**Pi `input`-Feld:** Nicht "Prompt-Tokens", sondern "wirklich nicht-gecachte neue Tokens
pro Turn". Bei Sonnet/Opus ≈ 1–3 Token pro Turn (Nachrichten-Boundary-Marker),
weil Pi auch den User-Prompt in `cacheWrite` packt.

**Rückrechnung Anzahl Turns:** `input = 3 + (Turns - 1) × 1`
→ `input=15` bei Sonnet-Real-Task = 13 Turns = 12 Tool-Calls

**`cacheRead` wächst pro Turn:** Pi cached bei jedem Turn nicht nur den
System-Prompt, sondern den gesamten bisherigen Gesprächsverlauf (Tool-Calls +
Ergebnisse). Summe über alle Turns ist entsprechend groß.

**Haiku (kein Caching):** Jede Nachricht vollständig in `input` → deutlich höhere
`input`-Summe bei gleicher Aufgabe.

## Konsequenz für Vergleiche

- `input`-Feld: **kein zuverlässiger Vergleichswert** zwischen Modellen
- **`total_tokens`** (Summe aller Felder) = ehrlichste Metrik; zählt alles was
  durch die API ging, unabhängig von Caching-Verhalten
- Alle Pi-Ergebnisse aus Tool-Runs **vor diesem Fix (2026-06-25)** sind ungültig
  und wurden verworfen

## Gilt nur für Pi

Claude Code gibt ein einzelnes JSON-Objekt am Ende aus (kein Multi-Turn-JSONL),
das bereits die Gesamtsumme enthält. Kein Summierungsproblem auf CC-Seite.
