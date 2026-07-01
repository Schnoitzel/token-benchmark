# ADR-0004: Plattform-Asymmetrie (CC = Windows, Pi = Linux) — betrifft alle Tool-/Laufzeit-Vergleiche

- **Status:** Akzeptiert
- **Datum:** 2026-06-30
- **Kontext:** Beim Sichten des neuen `medium-bash`-Laufs (in `benchmark-d1b7ef63.json`,
  Re-Run am 2026-06-30) fiel auf, dass CC trotz des fairen, environment-agnostischen
  Prompts (ADR-0003) weiterhin 14–22× Tokens mit riesiger Streuung verbraucht. Die
  Ursachenanalyse legte ein **grundlegenderes** Problem frei, als ADR-0003 adressiert hat.

## Befund

Die beiden Harnesses laufen in dieser Umgebung **nicht im selben Betriebssystem**:

| Harness | Binary-Pfad | Prozess läuft als |
|---|---|---|
| Pi | `…/node/.../@earendil-works/pi-coding-agent/dist/cli.js` (via nvm) | **Linux/WSL** nativ |
| Claude Code | `/mnt/c/Users/charalampakis.IOANNIS-PC/AppData/Roaming/npm/claude` | **Windows** (über `/mnt/c` im PATH) |

ADR-0003 hatte das schon notiert („CC läuft als Windows-Prozess"), aber nur den
`medium-bash`-Prompt repariert. Tatsächlich ist die Asymmetrie **nicht** auf einen
Prompt beschränkt — sie wirkt bei **jeder** Aufgabe, die Tools ausführt.

## Was betroffen ist — und was nicht

Entscheidend ist die Anzahl der Turns (= API-Roundtrips mit Tool-Ausführung):

| Task | CC `num_turns` (n=10) | OS-betroffen? |
|---|---|---|
| baseline-overhead, trivial-fact, trivial-math, simple-explain, medium-design, complex-refactor, complex-analysis | **1** | ❌ nein — reine Textantwort, keine Tools |
| simple-code | **2** (9/10) | ⚠️ leicht (erklärt die 29k→60k-Streuung) |
| medium-bash | **7–16** | ⚠️⚠️ stark |

**Kernunterscheidung:**
- **Single-Turn-Tasks (`num_turns=1`)** führen keine Tools aus → das OS ist für den
  Token-Verbrauch irrelevant. Die **Overhead-Kernzahl ~8× bleibt vollständig gültig.**
- **Multi-Turn-/Tool-Tasks** messen das agentische Verhalten — und dieses ist hier durch
  die Plattform verfälscht (Befehlsverfügbarkeit, Pfad-/Permission-Eigenheiten, CRLF/LF,
  WSL↔Windows-Brücke). Token, Turns und Laufzeit sind **nicht** sauber vergleichbar.

### Belege aus den Daten

1. **`medium-bash` (fairer Prompt, Re-Run 2026-06-30):** CC weiterhin 14–22×, Streuung
   95k–398k Tokens; CC erkennt durchgängig „Windows 10 Pro (MINGW64)", User
   `charalampakis` — also Windows-bash, nicht das Linux-bash, in dem Pi läuft. Der
   Prompt-Fix (ADR-0003) hat das OS-Wortlaut-Problem behoben, **nicht** die Plattform.
2. **Real-Task** (`repo_dir=/mnt/c/daten/datensicherung`, Windows-Pfad, 13–20 Turns):
   Pi greift als Linux-Prozess über die langsame WSL→Windows-Brücke (`/mnt/c`, 9P) auf
   dasselbe Repo zu, CC nativ unter Windows. Folge: **Pi liegt hier NICHT durchgängig
   vorne** — bei Haiku ist Pi sogar teurer und langsamer (630k/$0,128/78,9s vs.
   CC 605k/$0,120/61,4s); erst bei Opus klar vorne. Laufzeiten sind durchmischt.
3. **CRLF/LF** (bereits in `docs/quality-eval/2026-06-25-technische-erkenntnisse.md`):
   Windows-Repo mit CRLF, Pi schreibt LF zurück → nicht-deterministische Diffs, ~156
   Dateien als Seiteneffekt. Direktes OS-Artefakt.

## Entscheidung

1. **Overhead pro Anfrage (~8×) bleibt die belastbare Kernzahl** — beruht auf
   Single-Turn-Tasks, OS-unabhängig. Unverändert präsentierbar.
2. **Keine Effizienz-/Laufzeit-/„Pi-ist-günstiger-pro-Aufgabe"-Aussagen** aus den
   bisherigen Tool-/Real-Task-Daten ableiten. Insbesondere ist „Pi liegt in den
   Real-Tasks trotz Nachteil vorne" **faktisch falsch** (Haiku) und darf nicht in die
   Präsentation.
3. **Faire Tool-Messung erfordert gleiches OS für beide Harnesses.** Lösung: beide im
   **selben Container** (Linux) laufen lassen. Der Container ist damit nicht nur
   Distributions-Mittel für Kollegen, sondern die **methodische Messumgebung** für jeden
   Tool-Vergleich.
4. **`medium-bash` im Container neu fahren** (n=10, alle Modelle, beide Harnesses). Erst
   diese Zahlen sind als Tool-Overhead-Vergleich zitierfähig.
5. **Real-Task nicht neu fahren** (zu teuer). In Präsi/Doku nur mit explizitem Vorbehalt
   erwähnen: n=5, Einzelszenario, plattform-asymmetrisch, Ergebnis modellabhängig.

## Was eine faire Tool-Task-Messung zusätzlich braucht (für späteren Ausbau)

- **Identische Umgebung** (Container, gleiches OS/Tools) — siehe oben.
- **Self-contained Aufgabe** mit mitgelieferten Dateien statt Abfrage der Host-Umgebung
  (Reproduzierbarkeit).
- **Verifizierbares Erfolgskriterium** (Test grün / korrekte Zahl), damit nicht „weniger
  Turns bei falschem Ergebnis" als Sieg zählt.
- **Drei Metriken nebeneinander:** Tokens **+** `num_turns` **+** Erfolg. (`num_turns`
  steckt bereits im CC-`raw`, wird aber noch nicht ausgewertet.)

## Konsequenz

- `methodik.md`: Einschränkung „Plattform-Asymmetrie" ergänzt (verweist hierher).
- `docs/plans/2026-06-30-praesentation-und-doku.md`: Blocker + Container-Rolle + Real-Task-
  Formulierung angepasst; `medium-bash`-Container-Neulauf als Schritt vor der Ergebnis-Folie.
