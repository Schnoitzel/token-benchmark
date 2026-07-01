# Projekt: Token-Benchmark (Pi vs Claude Code)

## Worum geht es
POC für die "Summer Show": Vergleich des **Token-Verbrauchs und der Kosten**
zweier KI-Coding-Harnesses bei **identischen Prompts und Modellen**:
- **Pi** (minimalistisch, kleiner System-Prompt)
- **Claude Code** (feature-reich, großer System-Prompt)

Zusätzlich wird die **Antwortqualität** verglichen (Antworten beider Harnesses
werden nebeneinander gespeichert).

## Kernergebnis (bisher gemessen)
Claude Code hat ~**7–9,5× mehr System-Prompt-Overhead** (Tokens) und ~**4–5× höhere Kosten**
pro Anfrage – bei identischer Antwortqualität. Token-Faktor > Kosten-Faktor weil CCs Overhead
großteils aus billigem `cache_read` (0,10×) besteht. Rohdaten: `docs/evidence/`.
ADR Pi-Caching-Modellabhängigkeit: `docs/adr/0001-pi-caching-modellabhaengig.md`.
ADR Pi-Turn-Summierung (Tool-Runs): `docs/adr/0002-pi-turn-end-summierung.md`.

**Real-Task-Qualitätsvergleich** (2026-06-25, echtes JavaFX-Repo, visuell bewertet):
Bei unpräzisem Prompt liefern beide Harnesses ähnlich unvollständige Fixes –
bei drastisch unterschiedlichen Token-Zahlen und Laufzeiten. Details:
`docs/quality-eval/2026-06-25-real-task-ergebnisse.md` und
`docs/quality-eval/2026-06-25-technische-erkenntnisse.md`.

## Sprache
Mit dem Nutzer immer **auf Deutsch** kommunizieren. Code-Kommentare ebenfalls
deutsch. Der Nutzer ist **kein TypeScript-Kenner** → Tool ist in **Python**
geschrieben (reine Standardbibliothek, keine Abhängigkeiten).

## Aufbau (alles in diesem Ordner, Python 3.10+)
| Datei | Zweck |
|-------|-------|
| `server.py` | Web-Server für die UI (Start: `python3 server.py`) |
| `static/index.html` | Web-Oberfläche (HTML/CSS/JS, CSS-Diagramme, offline-fähig) |
| `core.py` | gemeinsame Benchmark-Logik (Generator `run_benchmark_iter`), einheitliche Kosten, Provenienz |
| `main.py` | CLI-Variante (nutzt `core.run_benchmark_iter`; `--repeat`, `--dry-run` etc.) |
| `models.py` | Modell-Definitionen (Haiku 4.5, Sonnet 4.6, Opus 4.8) |
| `pricing.py` | EINE Preistabelle; berechnet Kosten für BEIDE Harnesses aus Tokens |
| `tasks.py` | Aufgaben inkl. `baseline-overhead` (reiner Overhead-Messprompt) |
| `runners.py` | starten `pi`/`claude` als Subprozess (in Sandbox), parsen Token-JSON, Versions-Abfrage |
| `judge.py` | blinder LLM-Richter (Opus, Swap-Test) – Qualitätsbewertung |
| `report.py` | Markdown-Report-Generator (Median/Streuung, Baseline, Qualität, Provenienz) |
| `utils.py` | gemeinsame Helfer: `fmt_cost`/`fmt_n`/`ratio`, `load_suite`/`latest_suite_path`, `overhead_tokens` (EINE Quelle, kein Dup) |
| `stats.py` | Streuungsmaße (`median`/`stdev`/`iqr`/`rel_spread`/`summary`) + `build_aggregates` (Median+Streuung je Kombination) |
| `tests/` | `unittest`-Suite (Mocks, hermetisch) + Fixtures + opt-in Realmessung (`test_live_measurement`, `RUN_LIVE=1`) |
| `docs/methodik.md` | Erhebungsmethode + verifizierte Cache-Semantik (Referenz hinter den Zahlen) |
| `docs/evidence/` | versionierte Referenzläufe (JSON+Report) als zitierfähige Belege |
| `docs/plans/` | Feature-Workflow-Pläne (Single Source of Truth für den Fortschritt) |
| `docs/adr/` | Architecture Decision Records (harte Entscheidungen + Befunde mit Datum) |
| `.github/workflows/tests.yml` | CI: fährt Unit-Tests bei Push/PR (keine Live-Kosten) |
| `results/` | JSON-Rohdaten + Markdown-Berichte (auto, gitignored) |

## Tests & Entwicklung
- **Tests:** `python3 -m unittest discover -s tests` (schnell, Mocks, kostenlos).
  Reale Messung: `RUN_LIVE=1 python3 -m unittest tests.test_live_measurement`.
- **Aggregate:** Suite-JSON enthält `aggregates` (Median+Streuung je
  task×model×harness) via `stats.build_aggregates` → UI/Report ohne Neuberechnung.
- **`/api/config`** liefert auch `pricing` (Preise + Cache-Faktoren) → UI hat
  KEINE hartkodierten Preise mehr (siehe `server.build_config`).
- **UI** (`static/index.html`): Theme-Umschalter (dunkel/hell, localStorage),
  „Präsentieren“-Slide (3 Kernzahlen), Drill-down „Wie erhoben?“, Provenienz-Panel.
  Token-Breakdown: alle Felder einzeln (input / cache↑write / cache↓read / output /
  Overhead / Total), Tooltips auf jeder Spalte, Kosten-Breakdown im Drill-down,
  5-Min-Cache-Callout. Offen (Version 2): Multi-Slides.
- **Verifizierte Kernzahl:** Overhead = `input+cache_read+cache_write`; Pi Haiku
  ohne Caching (~3,1k), Pi Sonnet/Opus mit Caching (ebenfalls ~3,1k Overhead,
  aber kalt/warm-Kostenvariation ~2,3×); CC mit Prompt-Cache (~27–29k) → ~7–9,5×
  Token, ~4–5× Kosten, Qualität ≈ gleich. Details: `docs/methodik.md`,
  ADR: `docs/adr/0001-pi-caching-modellabhaengig.md`.
- **Workflow:** Feature-Workflow-Skill; Implementierung via Subagenten
  (`worker`), Health-Checks `architect`/`overseer` alle ~3 Schritte + Phasenende,
  `reviewer` am Phasenende. Plan-Ticks als eigene Commits, Red→Green sichtbar.

## Wichtige technische Details
- **Pi hängt bei offener stdin** im `-p`-Modus → alle Subprozesse mit
  `stdin=subprocess.DEVNULL` starten (siehe `runners.py`, `_run_process`).
- **Sandbox/Blank:** Beide Harnesses laufen in einem LEEREN temporären
  Arbeitsverzeichnis (`tempfile.TemporaryDirectory`, `cwd=`). Sonst entdeckt
  v.a. Claude Code projekteigene `AGENTS.md`/`CLAUDE.md` und schnüffelt per Tools
  herum. `--no-context-files` allein reicht NICHT (verhindert nur Auto-Laden).
- **Real-Tasks (`complexity="real"`):** Harness läuft direkt im echten Repo
  (`task.repo_dir`). Kein Auto-Reset – Nutzer prüft UI-Änderungen visuell, dann
  Reset per UI-Button (`/api/reset-repo`, preserviert `gdi-datensicherung.json`)
  oder `git restore .`. Timeout: 600s. `git diff` wird nach dem Run erfasst und
  an die Antwort angehängt.
- **Pi turn_end-Summierung (KRITISCH):** Pi meldet Token **pro Turn**, nicht
  kumulativ. Bei Tool-Runs alle `turn_end`-Events summieren (ADR-0002).
  Nur das letzte `turn_end` zu lesen liefert falsche (zu niedrige) Zahlen.
- **Pi `input`-Feld bei Tool-Runs:** ≈ 1–3 Token pro Turn (Nachrichten-Boundary),
  weil Pi auch den User-Prompt in `cacheWrite` packt. `input` ist kein
  verlässlicher Vergleichswert – `total_tokens` verwenden (ADR-0002).
- **Sofort-Speicherung:** `core.py` schreibt Suite-JSON nach **jedem Einzel-
  ergebnis** auf Disk (nicht erst am Ende). Verhindert Datenverlust bei
  Verbindungsabbruch.
- **Pi-Flags:** `-p --mode json --no-session --no-context-files --no-prompt-templates --thinking off --model <id>`
- **Claude-Flags:** `-p --output-format json --model <alias> --allow-dangerously-skip-permissions`
  (kein `--bare`, weil das nur API-Key-Login erlaubt; Nutzer hat nur OAuth.)
- **Token-Felder:** `cache_write` = System-Prompt beim 1. Aufruf, `cache_read` =
  gecacht bei Folgeaufrufen. `cache`-Summe = Overhead-Metrik.
- **Baseline-Overhead** (`baseline-overhead`-Task): Trivial-Prompt → `input+cache`
  ist praktisch nur System-Prompt + Tools. Gemessen: ~3,1k (Pi) vs ~27–29k (CC)
  = **~7–9,5×** (modellabhängig). Siehe `docs/evidence/` für Rohdaten.
- **Pi-Caching modellabhängig:** Haiku 4.5 kein Cache (overhead = input only);
  Sonnet 4.6 + Opus 4.8 aktivieren server-seitiges Caching ab run#1 (overhead
  stabil, Kosten kalt/warm ~2,3×). ADR: `docs/adr/0001`.
- **Kosten einheitlich:** `pricing.py` rechnet die Kosten für BEIDE aus den Tokens
  (eine Anthropic-Preisliste). Harness-Eigenangabe bleibt als `cost_harness_usd`.
  Wichtig: Overhead ~7–9,5× Tokens, aber Kosten nur ~4–5× (CC-Overhead ist billiger
  `cache_read`).
- **Wiederholungen:** `repeat` (UI-Feld / `--repeat`). Report zeigt Median + min–max + n.
- **Provenienz:** Suite-JSON enthält `provenance` (Versionen, Flags, Preise, Plattform).
- **Qualität:** `judge.py` (Opus als Richter; bewertet er Opus-Antworten → Sonnet).
  Blind (A/B), Swap-Test (2 Durchläufe/Paar). UI-Button „Qualität bewerten" →
  `/api/judge` (SSE). Ergebnis landet als `quality` in der Suite-JSON.
- **UI-Chips:** nur auf `change`-Event hören (kein manuelles `input.checked`-Toggle,
  sonst Doppel-Toggle-Bug mit Labels).
- **Umgebung: WSL** (Linux unter Windows). Kein Linux-Browser → UI im
  Windows-Browser unter `http://localhost:8000` öffnen. `server.py` versucht
  das via `explorer.exe` automatisch.

## Modell-IDs (verifiziert)
| Label | Pi (`--model`) | Claude Code (`--model`) |
|-------|----------------|-------------------------|
| Haiku 4.5 | `claude-haiku-4-5` | `haiku` |
| Sonnet 4.6 | `claude-sonnet-4-6` | `sonnet` |  <!-- korrigiert 2026-06-25, war 4-5 -->
| Opus 4.8 | `claude-opus-4-8` | `opus` |

## Bedienung
```bash
# UI (empfohlen)
python3 server.py        # dann http://localhost:8000 im Windows-Browser

# CLI
python3 main.py --dry-run
python3 main.py --complexity baseline --repeat 5   # Overhead-Kernzahl, belastbar
python3 main.py --complexity trivial --models "Sonnet 4.6"
python3 judge.py         # blinde Qualitätsbewertung des neuesten Laufs
python3 report.py        # Bericht aus neuestem Lauf (inkl. Qualität, falls bewertet)
```

## Mögliche nächste Schritte (offen)
- ~~LLM-as-judge~~ ✅ erledigt (`judge.py`, UI-Button, Report-Abschnitt)
- ~~Token-Breakdown~~ ✅ erledigt (UI + Report, alle Felder einzeln, 2026-06-25)
- ~~Sonnet-ID-Fix~~ ✅ erledigt (`claude-sonnet-4-6`, 2026-06-25)
- ~~Real-Task-Infrastruktur~~ ✅ erledigt (`repo_dir`, Reset-Button, git diff, 2026-06-25)
- ~~turn_end-Parser-Fix~~ ✅ erledigt (ADR-0002, 2026-06-25)
- **Real-Task-Runs abschließen:** Pi Opus (Re-Run) + alle 3 CC-Modelle noch
  offen. Qualitätsdoku: `docs/quality-eval/2026-06-25-real-task-ergebnisse.md`.
- ~~Phase E (Referenzlauf n=10)~~ ✅ gefahren (540 Runs, `results/benchmark-d1b7ef63.json`,
  2026-06-29); **aber** `medium-bash` war unfair → ersetzt (ADR-0003) und läuft neu.
- **Präsentation + Doku + Container** (Summer Show): schlanke Präsi (≤10 min),
  2 PDFs (Methodik/Ergebnisse + Nutzung/Ausblick), Container für Kollegen ohne
  Real-Task. Plan: `docs/plans/2026-06-30-praesentation-und-doku.md`.
  **Gated:** wartet auf neue `medium-bash`-Daten + User-Go.
- **Phase F (Quellen):** Anthropic-Docs belegen (Cache-TTL für Claude-4 verifizieren),
  Inferenzen kennzeichnen (Plan Phase F, selber Plan)
- Multi-Slides im Präsentationsmodus
- Mehr/billigere Modelle in `models.py` ergänzen
- Bei Preisänderungen `pricing.py` aktualisieren (Stand: Juni 2026)
