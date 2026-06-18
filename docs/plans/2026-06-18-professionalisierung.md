# Professionalisierung Token-Benchmark (Pi vs Claude Code)

- **Status:** In Progress
- **Date:** 2026-06-18
- **Branch/Worktree:** main (kleine, in sich geschlossene Schritte; bei Bedarf Feature-Branches)

## Problem
Der POC funktioniert und ist sauber strukturiert, aber für die "Summer Show"
und einen kritischen Auftritt fehlen drei Dinge: ein **Engineering-Fundament**
(Git ✅, Tests ❌), **wasserdichte, belastbare Zahlen** (Statistik, verifizierte
Cache-Semantik) und eine **show-taugliche, nachvollziehbare Darstellung** in der
UI. Querschnittsanforderung des Nutzers: **jede dargestellte Zahl muss zeigen,
wie sie erhoben wurde.**

## Scope
### In scope
- Test-Suite: Unit-Tests (Mocks, kostenlos) + reale Mess-Tests (echte Tokens).
- Verifikation der Cache-/Overhead-Semantik an echten Rohdaten.
- Statistische Belastbarkeit: Streuung/Konfidenz im Report **und** JSON.
- UI: beide Modi (gespeicherte Läufe + Live-Prompt) anschaulich aufbereiten,
  mit Drill-down zu Rohdaten + Erhebungsmethode; Export/Präsentations-Ansicht;
  Robustheit für Live-Demo.
- Nachvollziehbarkeit als Querschnitt (Provenienz überall sichtbar).

### Out of scope (vorerst)
- Neue Modelle/Tasks inhaltlich erweitern (nur falls nötig).
- Externe Laufzeit-Abhängigkeiten (Tool bleibt stdlib-only).
- Andere Provider als Anthropic.

## Approach
Strikte Reihenfolge **1 → 2 → 3** (vom Nutzer bestätigt). Jede Phase endet in
einem lauffähigen, committeten Zustand.

**Entscheidung Test-Framework:** stdlib `unittest` statt `pytest`. Begründung:
Das Alleinstellungsmerkmal des Projekts ist "null Abhängigkeiten, pur Python".
Mit `unittest` läuft die Test-Suite überall ohne Installation
(`python3 -m unittest`) - konsistent mit der Projekt-DNA und ein starkes
Argument vor technischem Publikum. (Aufwand ggü. pytest minimal.)

**Entscheidung reale Mess-Tests:** kosten Geld/Zeit und brauchen `pi`/`claude`
im PATH → standardmäßig **übersprungen**, nur per Opt-in (`RUN_LIVE=1`)
ausgeführt. So bleibt die Standard-Suite schnell und CI-tauglich, die belastbaren
Realmessungen sind aber jederzeit reproduzierbar abrufbar.

## Design

### Neue/zu ändernde Dateien
| Datei | Art | Zweck |
|-------|-----|-------|
| `tests/__init__.py` | neu | Test-Paket |
| `tests/fixtures/pi_turn_end.jsonl` | neu | echte Pi-JSONL-Beispielausgabe (anonymisiert) |
| `tests/fixtures/claude_result.json` | neu | echte Claude-JSON-Beispielausgabe |
| `tests/test_pricing.py` | neu | Unit: `compute_cost`, Cache-Multiplikatoren, unbekanntes Modell |
| `tests/test_judge.py` | neu | Unit: `extract_json`, Gewinner-Mapping, Swap/Bias, `overall` |
| `tests/test_report.py` | neu | Unit: `med`/`spread`/`ratio`/`_overhead_rows`, Aggregation |
| `tests/test_runners.py` | neu | Unit: Parsing aus Fixtures (subprocess gemockt) |
| `tests/test_core.py` | neu | Unit: `filter_models`/`filter_tasks`, `apply_unified_cost` |
| `tests/test_stats.py` | neu | Unit: neue Streuungs-Funktionen |
| `tests/test_live_measurement.py` | neu | **real**, opt-in: Baseline-Overhead n>1, Plausi + niedrige Streuung |
| `stats.py` | neu | gemeinsame Statistik (median, stdev, IQR, rel. Streuung) |
| `report.py` | ändern | Streuung/Konfidenz ausweisen; Cache-Semantik-Hinweis |
| `core.py` | ändern | Streuungs-Kennzahlen in Suite-JSON; ggf. Default-`repeat` |
| `pricing.py` | ggf. | Doc/Stand prüfen |
| `static/index.html` | ändern | Drill-down, Methodik-Panel, Präsentationsmodus, Export, Robustheit |
| `server.py` | ggf. | Export-Endpunkt; robustere Fehlerausgabe im SSE |
| `docs/methodik.md` | neu | Erhebungsmethode + Cache-Befund dokumentiert (verlinkt aus UI/Report) |
| `.github/workflows/tests.yml` | neu (optional) | CI: Unit-Tests bei jedem Push |
| `README.md` | ändern | Test-Aufruf, Methodik-Link, Phasen-Stand |

### Integrationspunkte (bestehend)
- Token-Parsing: `runners.py:run_pi` (turn_end/usage), `runners.py:run_claude`.
- Kosten: `pricing.cost_for_usage` ← `core.apply_unified_cost`.
- Aggregation/Report: `report.py` (`_overhead_rows`, `spread`, `build_markdown`).
- UI-Daten: `/api/config`, `/api/results`, `/api/result`, `/api/run`, `/api/judge`
  in `server.py`; Rendering in `static/index.html` (`renderResults`, `renderQuality`).

## Task Breakdown

### Phase 1 - Engineering-Fundament & Tests
- [x] 1.1 `docs/plans/` + diesen Plan committen. - erledigt (Commit `caa3629`).
- [x] 1.2 Echte Beispielausgaben einmal real erzeugen und als Fixtures ablegen
  (eine Pi-JSONL, eine Claude-JSON) - Grundlage für Parser-Tests. - erledigt.
  Befund: Pi `input=3068`, cache=0; CC overhead ~29k (`cache_read=21506`,
  `cache_write=7714`) → ~9,5×. Fliesst in Phase 2.1/methodik.md ein.
- [x] 1.3 `tests/test_pricing.py`: bekannte Modelle, Cache-Faktoren, unbekanntes
  Modell → `None`, dict- und Objekt-Eingabe. - 11 Tests, grün.
- [x] 1.4 `tests/test_judge.py`: `extract_json` (Code-Fences/Begleittext/kaputt),
  `map_winner` über beide Swap-Durchläufe, Bias→tie, `overall`-Mittel. - 18 Tests, grün.
- [x] 1.5 `tests/test_runners.py`: Parsing aus Fixtures (subprocess.run gemockt,
  inkl. Timeout- und Fehlerpfad). - 9 Tests, grün.
- [x] 1.6 `tests/test_report.py`: `med`/`spread`/`ratio`/`_overhead_rows`,
  Baseline-Bevorzugung, Fehler-Ausschluss. - 11 Tests, grün.
- [x] 1.7 `tests/test_core.py`: Filter + `apply_unified_cost` (Harness-Wert bleibt
  in `cost_harness_usd`, `cost_usd` wird einheitlich überschrieben). - 9 Tests, grün.
- [x] 1.8 README: Abschnitt "Tests" (`python3 -m unittest discover -s tests`). - erledigt.
- [x] 1.9 GitHub-Actions-Workflow für Unit-Tests (öffentlich, gratis; nur Mocks,
  keine Live-Kosten). - erledigt (`.github/workflows/tests.yml`).

### Phase 2 - Zahlen wasserdicht (Methodik)
- [x] 2.0 **Refactor `utils.py`** (aus architect-Befund): gemeinsame Helfer
  konsolidieren - `fmt_cost`/`fmt_n`/`ratio` (Inkonsistenz main `.4f` vs report
  `.3f` → vereinheitlicht `.4f`), `load_suite`/`latest_suite_path`,
  `overhead_tokens(usage)`. Test-first (13 Tests), Suite 77 grün,
  report/judge/main importieren daraus, CLI+Report end-to-end geprueft.
- [x] 2.1 **Cache-Semantik verifizieren:** Baseline real (Haiku, 5x). Befund:
  Pi kein Caching (Overhead=input 3069); CC Prompt-Cache (29296 = input 10 +
  cache_read 21506 + cache_write 7778); Total-Overhead warm/kalt-stabil (σ<2);
  Faktor 9,55×. Dokumentiert in `docs/methodik.md`.
- [x] 2.2 Overhead-Erzählung an Befund angleichen: report.py-Footer + README
  korrigiert (Overhead=input+cache_read+cache_write, Pi ohne Cache vs CC mit
  Prompt-Cache, ~9,5× Token / ~5× Kosten), Verweis auf docs/methodik.md.
- [x] 2.3 `stats.py`: `median`, `stdev`, `iqr`, `min/max`, `rel_spread`, `n` + `summary()`. — 10 Tests, grün.
- [x] 2.4 `core.py`: Aggregate (Median+Streuung je Kombination) via
  stats.build_aggregates in suite['aggregates']. — 5 Tests, grün.
- [x] 2.5 `report.py`: Baseline-Block weist Median + min-max + n + relative
  Streuung (Belastbarkeit) aus. — +2 Tests, grün.
- [x] 2.6 Default-`repeat` begründet: Default bleibt 1 (Kosten/Exploration),
  Empfehlung `--repeat 5` fuer belastbare Zahlen — dokumentiert in methodik.md.
- [x] 2.7 `tests/test_stats.py`: Unit-Tests der Statistik (median/stdev/iqr/
  rel_spread/summary/build_aggregates). — 14 Tests, test-first in 2.3/2.4.
- [ ] 2.8 `tests/test_live_measurement.py` (**real, opt-in `RUN_LIVE=1`**):
  Baseline-Overhead für ein günstiges Modell, n>1; prüft Plausibilität
  (CC-Overhead deutlich > Pi) und **niedrige relative Streuung** (Reproduzierbarkeit).
- [ ] 2.9 Einen belastbaren Referenzlauf erzeugen, Befund + Zahlen in
  `docs/methodik.md` dokumentieren. Commit + Push.

### Phase 3 - Show-ready (Präsentation & Nachvollziehbarkeit)
- [ ] 3.1 **Methodik-/Provenienz-Panel** in der UI: Versionen, Flags, Sandbox,
  Preise, Cache-Faktoren, n - immer einsehbar (aus `provenance`).
- [ ] 3.2 **Drill-down je Kennzahl:** von jeder KPI/Balken/Tabelle zu den
  Roh-Tokens und der Rechenformel (Tooltip/Aufklapp "Wie wurde das erhoben?").
- [ ] 3.3 Streuung in der UI sichtbar (Fehlerbalken/Spanne, n-Anzeige) - KPI-Kacheln
  korrekt aggregieren (Median statt Summe über Wiederholungen).
- [ ] 3.4 **Präsentationsmodus:** aufgeräumte, großflächige Ansicht der Kernzahlen
  (Overhead-Faktor, Kostenfaktor, Qualitäts-Delta) für Beamer.
- [ ] 3.5 **Live-Robustheit:** Fehler/Timeouts sichtbar abfangen, Buttons sperren,
  SSE-Abbruch sauber behandeln, klare Status-Hinweise.
- [ ] 3.6 **Export:** Markdown-Download (Report) per Button; PDF optional via
  Druckansicht (`window.print()` + Print-CSS - ohne Abhängigkeit).
- [ ] 3.7 Beide Modi prominent: gespeicherte Läufe laden **und** Live-Prompt
  eingeben, klar getrennt und erklärt.
- [ ] 3.8 README + `docs/methodik.md` final, Screenshots optional. Commit + Push.

## Test Strategy
- **Ausführen:** `python3 -m unittest discover -s tests` (schnell, kostenlos,
  Standard). Reale Messung: `RUN_LIVE=1 python3 -m unittest tests.test_live_measurement`.
- **Unit (Mocks):** reine Logik ohne Netz/Subprozess - Pricing, Judge-Parsing &
  -Mapping, Report-Aggregation, Stats, Filter, Runner-Parsing (Fixtures).
- **Integration/real:** belastbare Token-Messung, opt-in, prüft Plausibilität +
  Reproduzierbarkeit (relative Streuung unter Schwelle), nicht exakte Festwerte
  (Modelle/Versionen ändern sich).
- **Edge-Cases:** unbekanntes Modell, leere/kaputte Judge-Antwort, Positions-Bias,
  Timeout, fehlerhafte Läufe aus Statistik ausgeschlossen, leere Eingaben.

## Risks & Open Questions
- **Cache-Befund kann die Kern-Erzählung verschieben** (2.1) → zuerst klären,
  Texte danach anpassen. Risiko-mindernd: ehrliche Dokumentation in `docs/methodik.md`.
- Reale Tests sind nicht-deterministisch → nur Plausibilität/Streuung prüfen,
  keine harten Festwerte.
- PDF rein per Druck-CSS (keine Abhängigkeit) → Layout muss druckfreundlich sein.
- Offen: Soll der GitHub-Actions-Workflow (1.9) wirklich rein? (Nur Unit-Tests,
  keine Live-Kosten.) → Default: ja, da reiner Mehrwert.

## Definition of Done
- [ ] Unit-Test-Suite grün via `python3 -m unittest`; deckt Pricing, Judge, Report,
  Stats, Core-Filter, Runner-Parsing ab.
- [ ] Mind. ein **realer** Mess-Test liefert die Overhead-Kernzahl reproduzierbar
  (n>1, inkl. Streuung), opt-in lauffähig.
- [ ] Cache-/Overhead-Semantik verifiziert und in `docs/methodik.md` dokumentiert.
- [ ] Report **und** UI weisen für jede Zahl Median + Streuung + n + Herkunft aus;
  Drill-down zu Rohdaten/Formel vorhanden.
- [ ] UI demonstriert gespeicherte + Live-Ergebnisse, show-tauglich robust,
  Präsentationsmodus + Export vorhanden.
- [ ] Alles committet und nach GitHub gepusht.
