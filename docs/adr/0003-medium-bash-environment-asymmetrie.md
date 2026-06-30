# ADR-0003: medium-bash war environment-asymmetrisch — Aufgabe ersetzt

- **Status:** Akzeptiert
- **Datum:** 2026-06-29
- **Kontext:** Analyse der benchmark-d1b7ef63.json-Ergebnisse nach Abschluss der 540 Runs

## Problem

Der ursprüngliche `medium-bash`-Task fragte nach den 5 größten Dateien unter
`/usr/share/doc` — einem Linux-spezifischen Pfad. Pi läuft nativ in WSL und
findet diesen Pfad sofort. Claude Code läuft als **Windows-Prozess** und hat
keinen verlässlichen Zugriff auf WSL-Dateisystempfade.

### Messdaten (n=10, alle Modelle)

| Harness · Modell | `/usr/share/doc` gefunden | Verhalten |
|---|---|---|
| Pi · alle 3 Modelle | **10/10** | stabil, sofort gefunden |
| CC · Haiku 4.5 | 8/10 (6/10 nicht gefunden) | inkonsistent |
| CC · Sonnet 4.6 | 10/10 (1/10 „not present") | gefunden, aber Overhead 116k–396k Tokens (!) |
| CC · Opus 4.8 | 10/10 erwähnt, **10/10 nicht gefunden** | „the directory simply isn't present on this machine" |

### Folgen der Asymmetrie

1. **CC · Opus**: Konnte die Aufgabe nie lösen — alle 10 Runs scheiterten. Trotzdem ~82.988 Tokens Overhead pro Run (~$0,33).
2. **CC · Sonnet**: Fand den Pfad, aber mit massiver Streuung (116k–396k Tokens). Das Modell suchte extensiv, weil der Zugriff nicht direkt möglich war.
3. **Der gemessene 31×-Token-Faktor** für CC Sonnet medium-bash spiegelt keine harness-bedingte Overhead-Differenz wider, sondern environment-bedingtes Suchverhalten.
4. **CC · Haiku** Overhead-Streuung: min=58.717, max=182.523 (3× Varianz) — zeigt instabiles, umgebungsabhängiges Verhalten.

### Vergleich: andere Tasks

Alle anderen Tasks haben < 0,1 % Streuung im Overhead. medium-bash war der einzige Task mit environment-bedingter Nicht-Reproduzierbarkeit.

## Entscheidung

`medium-bash` wird durch eine **environment-agnostische Shell-Aufgabe** ersetzt:

```
Using your shell tools, gather the following system information and present
it as a formatted table:
1. Current working directory and current username
2. Operating system name and version
3. Number of available CPU cores
4. Total and free disk space on the main volume

Use the appropriate shell commands for your environment (Linux/macOS or
Windows). End with one sentence summarising the most notable aspect of
this environment.
```

### Warum diese Aufgabe fair ist

- **Keine fest codierten Linux-Pfade** — jeder Harness nutzt die für seine Umgebung passenden Befehle
- **Mehrere Tool-Calls nötig** (4–5 separate Befehle) — Tool-Overhead bleibt messbar
- **Klare Korrektheitskriterien** — alle 4 Datenpunkte müssen vorhanden sein
- **Deterministisch** — Systeminfos ändern sich nicht zwischen Runs

## Konsequenz

- Alle 60 `medium-bash`-Ergebnisse aus `benchmark-d1b7ef63.json` werden **ungültig** erklärt und aus der Auswertung entfernt.
- 60 Ersatz-Runs werden mit der neuen Aufgabe durchgeführt (n=10, alle 3 Modelle, beide Harnesses).
- Die Präsentation wird aktualisiert — der „31×-Ausreißer" entfällt, neue Zahlen folgen.
- `methodik.md` erhält einen Hinweis: Tool-Tasks müssen auf environment-Symmetrie geprüft werden.

## Offene Frage

Warum konnte CC Sonnet `/usr/share/doc` in 10/10 Runs finden während CC Opus es nie fand? Möglicherweise sucht Sonnet breiter (mehr Tool-Calls) und trifft dabei zufällig den richtigen Pfad über WSL-Mounting. Nicht weiter untersucht.
